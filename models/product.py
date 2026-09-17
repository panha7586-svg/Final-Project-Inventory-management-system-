
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict


class Product:

    product_id: str
    name: str
    sku: str
    category: str
    quantity: int
    cost_price: float
    selling_price: float
    supplier_id: str | None
    reorder_level: int
    active: bool
    created_at: str
    updated_at: str

    def __init__(
        self,
        name: str,
        sku: str,
        category: str,
        quantity: int,
        cost_price: float,
        selling_price: float,
        supplier_id: str | None = None,
        reorder_level: int = 10,
        product_id: str | None = None,
        active: bool = True,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        self.product_id = product_id or str(uuid.uuid4())
        self.name = name
        self.sku = sku
        self.category = category
        self.quantity = int(quantity)
        self.cost_price = float(cost_price)
        self.selling_price = float(selling_price)
        self.supplier_id = supplier_id
        self.reorder_level = int(reorder_level)
        self.active = bool(active)
        self.created_at = created_at or datetime.now().isoformat(timespec="seconds")
        self.updated_at = updated_at or self.created_at

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat(timespec="seconds")

    def stock_value(self) -> float:
        return round(self.quantity * self.cost_price, 2)

    def is_low_stock(self, threshold: int | None = None) -> bool:
        limit = self.reorder_level if threshold is None else threshold
        return self.quantity <= limit

    def is_out_of_stock(self) -> bool:
        return self.quantity <= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "sku": self.sku,
            "category": self.category,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "selling_price": self.selling_price,
            "supplier_id": self.supplier_id,
            "reorder_level": self.reorder_level,
            "active": self.active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        return cls(
            name=str(data["name"]),
            sku=str(data["sku"]),
            category=str(data.get("category", "General")),
            quantity=int(data.get("quantity", 0)),
            cost_price=float(data.get("cost_price", 0.0)),
            selling_price=float(data.get("selling_price", 0.0)),
            supplier_id=data.get("supplier_id"),
            reorder_level=int(data.get("reorder_level", 10)),
            product_id=data.get("product_id"),
            active=bool(data.get("active", True)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def __repr__(self) -> str:
        return f"<Product {self.sku} - {self.name}>"
