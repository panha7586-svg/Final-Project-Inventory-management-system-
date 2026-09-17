
from __future__ import annotations

from typing import Optional, Any

from config import Settings, settings
from logger import setup_logger
from models.supplier import Supplier
from utils.json_handler import load_json, save_json

logger = setup_logger(settings.log_level)


class SupplierNotFoundError(Exception):
    pass


class SupplierService:

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.config = config or settings
        self.suppliers: list[Supplier] = self._load_suppliers()

    def _load_suppliers(self) -> list[Supplier]:
        raw = load_json(self.config.suppliers_file, default=[], data_dir=self.config.data_dir)
        return [Supplier.from_dict(item) for item in raw if isinstance(item, dict)]

    def _save_suppliers(self) -> None:
        if not save_json(
            self.config.suppliers_file,
            [supplier.to_dict() for supplier in self.suppliers],
            data_dir=self.config.data_dir,
        ):
            raise OSError("Unable to save supplier data.")

    def add_supplier(
        self,
        name: str,
        contact_person: str = "",
        phone: str = "",
        email: str = "",
        address: str = "",
    ) -> Supplier:
        if not name.strip():
            raise ValueError("Supplier name cannot be empty.")
        supplier = Supplier(name=name, contact_person=contact_person, phone=phone,
                            email=email, address=address)
        self.suppliers.append(supplier)
        self._save_suppliers()
        logger.info("Added supplier '%s'.", supplier.name)
        return supplier

    def get_all_suppliers(self, include_inactive: bool = False) -> list[Supplier]:
        if include_inactive:
            return list(self.suppliers)
        return [supplier for supplier in self.suppliers if supplier.active]

    def get_supplier_by_id(self, supplier_id: str) -> Supplier:
        for supplier in self.suppliers:
            if supplier.supplier_id == supplier_id:
                return supplier
        raise SupplierNotFoundError(f"Supplier with id '{supplier_id}' not found.")

    def search_suppliers(self, keyword: str) -> list[Supplier]:
        term = keyword.lower().strip()
        return [
            supplier
            for supplier in self.suppliers
            if term in supplier.name.lower()
            or term in (supplier.contact_person or "").lower()
            or term in (supplier.email or "").lower()
        ]

    def update_supplier(self, supplier_id: str, **fields: Any) -> Supplier:
        supplier = self.get_supplier_by_id(supplier_id)
        allowed = {"name", "contact_person", "phone", "email", "address", "active"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unknown supplier fields: {', '.join(sorted(unknown))}")
        for key, value in fields.items():
            if value is not None:
                setattr(supplier, key, value)
        if not supplier.name.strip():
            raise ValueError("Supplier name cannot be empty.")
        self._save_suppliers()
        return supplier

    def soft_delete_supplier(self, supplier_id: str) -> Supplier:
        supplier = self.get_supplier_by_id(supplier_id)
        supplier.active = False
        self._save_suppliers()
        logger.info("Soft-deleted supplier '%s'.", supplier.name)
        return supplier

    def hard_delete_supplier(self, supplier_id: str) -> None:
        supplier = self.get_supplier_by_id(supplier_id)
        self.suppliers = [item for item in self.suppliers if item.supplier_id != supplier_id]
        self._save_suppliers()
        logger.info("Hard-deleted supplier '%s'.", supplier.name)
