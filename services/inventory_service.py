
from __future__ import annotations

from typing import Any, Optional

from config import Settings, settings
from logger import setup_logger
from models.product import Product
from models.transaction import Transaction, TransactionType
from utils.json_handler import load_json, save_json

logger = setup_logger(settings.log_level)


class DuplicateSKUError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


class InventoryService:

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.config = config or settings
        self.products: list[Product] = self._load_products()
        self.transactions: list[Transaction] = self._load_transactions()

    def _load_products(self) -> list[Product]:
        raw = load_json(self.config.products_file, default=[], data_dir=self.config.data_dir)
        return [Product.from_dict(item) for item in raw if isinstance(item, dict)]

    def _save_products(self) -> None:
        if not save_json(
            self.config.products_file,
            [product.to_dict() for product in self.products],
            data_dir=self.config.data_dir,
        ):
            raise OSError("Unable to save product data.")

    def _load_transactions(self) -> list[Transaction]:
        raw = load_json(
            self.config.transactions_file,
            default=[],
            data_dir=self.config.data_dir,
        )
        return [Transaction.from_dict(item) for item in raw if isinstance(item, dict)]

    def _save_transactions(self) -> None:
        if not save_json(
            self.config.transactions_file,
            [transaction.to_dict() for transaction in self.transactions],
            data_dir=self.config.data_dir,
        ):
            raise OSError("Unable to save transaction data.")

    def sku_exists(self, sku: str, exclude_product_id: Optional[str] = None) -> bool:
        return any(
            product.sku.lower() == sku.lower()
            and product.product_id != exclude_product_id
            for product in self.products
        )

    def add_product(
        self,
        name: str,
        sku: str,
        category: str,
        quantity: int,
        cost_price: float,
        selling_price: float,
        supplier_id: Optional[str] = None,
        reorder_level: Optional[int] = None,
    ) -> Product:
        if self.sku_exists(sku):
            raise DuplicateSKUError(f"A product with SKU '{sku}' already exists.")
        if quantity < 0:
            raise ValueError("Initial quantity cannot be negative.")
        if cost_price < 0 or selling_price < 0:
            raise ValueError("Prices cannot be negative.")
        if reorder_level is None:
            reorder_level = self.config.low_stock_threshold
        if reorder_level < 0:
            raise ValueError("Reorder level cannot be negative.")

        product = Product(
            name=name,
            sku=sku,
            category=category,
            quantity=quantity,
            cost_price=cost_price,
            selling_price=selling_price,
            supplier_id=supplier_id,
            reorder_level=reorder_level,
        )
        self.products.append(product)
        try:
            self._save_products()
            if quantity > 0:
                self._record_transaction(
                    product.product_id,
                    TransactionType.STOCK_IN,
                    quantity,
                    unit_price=cost_price,
                    supplier_id=supplier_id,
                    note="Initial stock on product creation",
                )
        except Exception:
            self.products.remove(product)
            self._save_products()
            raise
        logger.info("Added product %s (%s).", product.sku, product.name)
        return product

    def get_all_products(self, include_inactive: bool = False) -> list[Product]:
        if include_inactive:
            return list(self.products)
        return [product for product in self.products if product.active]

    def get_product_by_id(self, product_id: str) -> Product:
        for product in self.products:
            if product.product_id == product_id:
                return product
        raise ProductNotFoundError(f"Product with id '{product_id}' not found.")

    def get_product_by_sku(self, sku: str) -> Product:
        for product in self.products:
            if product.sku.lower() == sku.lower():
                return product
        raise ProductNotFoundError(f"Product with SKU '{sku}' not found.")

    def search_products(
        self,
        keyword: str = "",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_stock: Optional[int] = None,
        max_stock: Optional[int] = None,
    ) -> list[Product]:
        if min_price is not None and min_price < 0:
            raise ValueError("Minimum price cannot be negative.")
        if max_price is not None and max_price < 0:
            raise ValueError("Maximum price cannot be negative.")
        if min_stock is not None and min_stock < 0:
            raise ValueError("Minimum stock cannot be negative.")
        if max_stock is not None and max_stock < 0:
            raise ValueError("Maximum stock cannot be negative.")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValueError("Minimum price cannot exceed maximum price.")
        if min_stock is not None and max_stock is not None and min_stock > max_stock:
            raise ValueError("Minimum stock cannot exceed maximum stock.")

        term = keyword.lower().strip()
        results: list[Product] = []
        for product in self.get_all_products():
            keyword_match = (
                not term
                or term in product.name.lower()
                or term in product.sku.lower()
                or term in product.category.lower()
            )
            price_match = (
                (min_price is None or product.selling_price >= min_price)
                and (max_price is None or product.selling_price <= max_price)
            )
            stock_match = (
                (min_stock is None or product.quantity >= min_stock)
                and (max_stock is None or product.quantity <= max_stock)
            )
            if keyword_match and price_match and stock_match:
                results.append(product)
        return results

    def get_low_stock_products(self) -> list[Product]:
        return [
            product
            for product in self.products
            if product.active and product.is_low_stock() and not product.is_out_of_stock()
        ]

    def get_out_of_stock_products(self) -> list[Product]:
        return [
            product
            for product in self.products
            if product.active and product.is_out_of_stock()
        ]

    def update_product(self, product_id: str, **fields: Any) -> Product:
        product = self.get_product_by_id(product_id)
        allowed = {
            "name", "sku", "category", "quantity", "cost_price", "selling_price",
            "supplier_id", "reorder_level", "active",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unknown product fields: {', '.join(sorted(unknown))}")
        if "sku" in fields and fields["sku"] and self.sku_exists(
            str(fields["sku"]), exclude_product_id=product_id
        ):
            raise DuplicateSKUError(f"A product with SKU '{fields['sku']}' already exists.")

        original = product.to_dict()
        try:
            for key, value in fields.items():
                if value is not None:
                    setattr(product, key, value)
            if product.quantity < 0 or product.cost_price < 0 or product.selling_price < 0:
                raise ValueError("Quantity and prices cannot be negative.")
            if product.reorder_level < 0:
                raise ValueError("Reorder level cannot be negative.")
            product.touch()
            self._save_products()
        except Exception:
            restored = Product.from_dict(original)
            index = self.products.index(product)
            self.products[index] = restored
            raise
        logger.info("Updated product %s.", product.sku)
        return product

    def soft_delete_product(self, product_id: str) -> Product:
        product = self.get_product_by_id(product_id)
        product.active = False
        product.touch()
        self._save_products()
        logger.info("Soft-deleted product %s.", product.sku)
        return product

    def hard_delete_product(self, product_id: str) -> None:
        product = self.get_product_by_id(product_id)
        self.products = [item for item in self.products if item.product_id != product_id]
        self._save_products()
        logger.info("Hard-deleted product %s.", product.sku)

    def _record_transaction(
        self,
        product_id: str,
        tx_type: str,
        quantity: int,
        unit_price: float = 0.0,
        supplier_id: Optional[str] = None,
        performed_by: str = "system",
        note: str = "",
    ) -> Transaction:
        transaction = Transaction(
            product_id=product_id,
            tx_type=tx_type,
            quantity=quantity,
            unit_price=unit_price,
            supplier_id=supplier_id,
            performed_by=performed_by,
            note=note,
        )
        self.transactions.append(transaction)
        try:
            self._save_transactions()
        except Exception:
            self.transactions.pop()
            raise
        return transaction

    def stock_in(
        self,
        product_id: str,
        quantity: int,
        unit_cost: Optional[float] = None,
        supplier_id: Optional[str] = None,
        performed_by: str = "system",
        note: str = "",
    ) -> Product:
        if quantity <= 0:
            raise ValueError("Stock-in quantity must be positive.")
        if unit_cost is not None and unit_cost < 0:
            raise ValueError("Unit cost cannot be negative.")
        product = self.get_product_by_id(product_id)
        old_values = (product.quantity, product.cost_price)
        product.quantity += quantity
        if unit_cost is not None:
            product.cost_price = unit_cost
        product.touch()
        try:
            self._save_products()
            self._record_transaction(
                product_id,
                TransactionType.STOCK_IN,
                quantity,
                unit_price=unit_cost if unit_cost is not None else product.cost_price,
                supplier_id=supplier_id or product.supplier_id,
                performed_by=performed_by,
                note=note,
            )
        except Exception:
            product.quantity, product.cost_price = old_values
            self._save_products()
            raise
        return product

    def stock_out(
        self,
        product_id: str,
        quantity: int,
        unit_price: Optional[float] = None,
        performed_by: str = "system",
        note: str = "",
    ) -> Product:
        if quantity <= 0:
            raise ValueError("Stock-out quantity must be positive.")
        if unit_price is not None and unit_price < 0:
            raise ValueError("Unit price cannot be negative.")
        product = self.get_product_by_id(product_id)
        if product.quantity < quantity:
            raise InsufficientStockError(
                f"Cannot remove {quantity} units — only {product.quantity} in stock for '{product.name}'."
            )
        old_quantity = product.quantity
        product.quantity -= quantity
        product.touch()
        try:
            self._save_products()
            self._record_transaction(
                product_id,
                TransactionType.STOCK_OUT,
                quantity,
                unit_price=unit_price if unit_price is not None else product.selling_price,
                performed_by=performed_by,
                note=note,
            )
        except Exception:
            product.quantity = old_quantity
            self._save_products()
            raise
        return product

    def record_purchase(
        self,
        product_id: str,
        quantity: int,
        unit_cost: float,
        supplier_id: str,
        performed_by: str = "system",
        note: str = "",
    ) -> Product:
        if quantity <= 0:
            raise ValueError("Purchase quantity must be positive.")
        if unit_cost < 0:
            raise ValueError("Unit cost cannot be negative.")
        if not supplier_id.strip():
            raise ValueError("Supplier ID is required for a purchase.")
        product = self.get_product_by_id(product_id)
        old_values = (product.quantity, product.cost_price, product.supplier_id)
        product.quantity += quantity
        product.cost_price = unit_cost
        product.supplier_id = supplier_id
        product.touch()
        try:
            self._save_products()
            self._record_transaction(
                product_id,
                TransactionType.PURCHASE,
                quantity,
                unit_price=unit_cost,
                supplier_id=supplier_id,
                performed_by=performed_by,
                note=note,
            )
        except Exception:
            product.quantity, product.cost_price, product.supplier_id = old_values
            self._save_products()
            raise
        return product

    def adjust_stock(
        self,
        product_identifier: str,
        delta: int,
        performed_by: str = "system",
        note: str = "Batch stock adjustment",
    ) -> Product:
        if delta == 0:
            raise ValueError("Adjustment quantity cannot be zero.")
        try:
            product = self.get_product_by_id(product_identifier)
        except ProductNotFoundError:
            product = self.get_product_by_sku(product_identifier)
        if product.quantity + delta < 0:
            raise InsufficientStockError(
                f"Adjustment would make '{product.name}' stock negative."
            )

        old_quantity = product.quantity
        product.quantity += delta
        product.touch()
        try:
            self._save_products()
            self._record_transaction(
                product.product_id,
                TransactionType.ADJUSTMENT,
                delta,
                unit_price=product.cost_price,
                performed_by=performed_by,
                note=note,
            )
        except Exception:
            product.quantity = old_quantity
            self._save_products()
            raise
        return product

    def get_transactions_for_product(self, product_id: str) -> list[Transaction]:
        return [tx for tx in self.transactions if tx.product_id == product_id]

    def get_all_transactions(self) -> list[Transaction]:
        return list(self.transactions)
