
from __future__ import annotations

from typing import Any

from logger import setup_logger
from models.transaction import TransactionType

logger = setup_logger()


class ReportService:

    def __init__(self, inventory_service: Any, supplier_service: Any) -> None:
        self.inventory_service = inventory_service
        self.supplier_service = supplier_service

    def summary(self) -> dict[str, Any]:
        products = self.inventory_service.get_all_products()
        suppliers = self.supplier_service.get_all_suppliers()
        categories = {product.category for product in products}
        return {
            "total_products": len(products),
            "total_categories": len(categories),
            "total_suppliers": len(suppliers),
            "low_stock_count": len(self.inventory_service.get_low_stock_products()),
            "out_of_stock_count": len(self.inventory_service.get_out_of_stock_products()),
            "total_inventory_value": round(sum(p.stock_value() for p in products), 2),
            "total_potential_revenue": round(
                sum(p.quantity * p.selling_price for p in products), 2
            ),
        }

    def stock_out_history(self) -> list[Any]:
        txs = [
            tx for tx in self.inventory_service.get_all_transactions()
            if tx.tx_type == TransactionType.STOCK_OUT
        ]
        return sorted(txs, key=lambda tx: tx.timestamp, reverse=True)

    def sales_revenue_summary(self) -> dict[str, Any]:
        stock_outs = self.stock_out_history()
        return {
            "total_units_sold": sum(tx.quantity for tx in stock_outs),
            "total_revenue": round(sum(tx.total_value() for tx in stock_outs), 2),
            "transaction_count": len(stock_outs),
        }

    def purchase_history(self) -> list[Any]:
        txs = [
            tx for tx in self.inventory_service.get_all_transactions()
            if tx.tx_type in (TransactionType.PURCHASE, TransactionType.STOCK_IN)
        ]
        return sorted(txs, key=lambda tx: tx.timestamp, reverse=True)

    def category_breakdown(self) -> dict[str, dict[str, float | int]]:
        breakdown: dict[str, dict[str, float | int]] = {}
        for product in self.inventory_service.get_all_products():
            entry = breakdown.setdefault(product.category, {"count": 0, "quantity": 0, "value": 0.0})
            entry["count"] = int(entry["count"]) + 1
            entry["quantity"] = int(entry["quantity"]) + product.quantity
            entry["value"] = float(entry["value"]) + product.stock_value()
        for entry in breakdown.values():
            entry["value"] = round(float(entry["value"]), 2)
        return breakdown

    def product_turnover_analysis(self) -> list[dict[str, Any]]:
        sold_by_product: dict[str, int] = {}
        for tx in self.stock_out_history():
            sold_by_product[tx.product_id] = sold_by_product.get(tx.product_id, 0) + tx.quantity

        results: list[dict[str, Any]] = []
        for product in self.inventory_service.get_all_products():
            units_sold = sold_by_product.get(product.product_id, 0)
            stock_base = units_sold + max(product.quantity, 0)
            turnover_rate = round(units_sold / stock_base, 4) if stock_base else 0.0
            results.append({
                "sku": product.sku,
                "product": product.name,
                "units_sold": units_sold,
                "current_stock": product.quantity,
                "turnover_rate": turnover_rate,
            })
        return sorted(results, key=lambda row: row["turnover_rate"], reverse=True)

    def supplier_spending_ranking(self) -> list[dict[str, Any]]:
        spending: dict[str, float] = {}
        units: dict[str, int] = {}
        for tx in self.inventory_service.get_all_transactions():
            if tx.tx_type != TransactionType.PURCHASE:
                continue
            if not tx.supplier_id:
                continue
            spending[tx.supplier_id] = spending.get(tx.supplier_id, 0.0) + tx.total_value()
            units[tx.supplier_id] = units.get(tx.supplier_id, 0) + tx.quantity

        rows: list[dict[str, Any]] = []
        for supplier_id, amount in spending.items():
            try:
                supplier = self.supplier_service.get_supplier_by_id(supplier_id)
                supplier_name = supplier.name
            except Exception:
                supplier_name = supplier_id[:8]
            rows.append({
                "supplier_id": supplier_id,
                "supplier": supplier_name,
                "units_purchased": units[supplier_id],
                "spending": round(amount, 2),
            })
        return sorted(rows, key=lambda row: row["spending"], reverse=True)

    def profit_analysis(self) -> dict[str, Any]:
        revenue = 0.0
        estimated_cogs = 0.0
        units = 0
        by_product: list[dict[str, Any]] = []
        for tx in self.stock_out_history():
            try:
                product = self.inventory_service.get_product_by_id(tx.product_id)
                cost = product.cost_price
                sku = product.sku
                name = product.name
            except Exception:
                cost = 0.0
                sku = tx.product_id[:8]
                name = "Deleted product"
            tx_revenue = tx.total_value()
            tx_cogs = round(tx.quantity * cost, 2)
            revenue += tx_revenue
            estimated_cogs += tx_cogs
            units += tx.quantity
            by_product.append({
                "sku": sku,
                "product": name,
                "units_sold": tx.quantity,
                "revenue": round(tx_revenue, 2),
                "estimated_cogs": tx_cogs,
                "profit": round(tx_revenue - tx_cogs, 2),
            })

        revenue = round(revenue, 2)
        estimated_cogs = round(estimated_cogs, 2)
        profit = round(revenue - estimated_cogs, 2)
        margin = round((profit / revenue) * 100, 2) if revenue else 0.0
        return {
            "units_sold": units,
            "sales_revenue": revenue,
            "estimated_cogs": estimated_cogs,
            "gross_profit": profit,
            "gross_margin_percent": margin,
            "method": "COGS estimated using each product's current cost_price",
            "by_product": by_product,
        }
