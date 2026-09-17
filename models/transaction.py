
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar, Dict, Tuple


class TransactionType:

    STOCK_IN: ClassVar[str] = "STOCK_IN"
    STOCK_OUT: ClassVar[str] = "STOCK_OUT"
    PURCHASE: ClassVar[str] = "PURCHASE"
    ADJUSTMENT: ClassVar[str] = "ADJUSTMENT"
    ALL_TYPES: ClassVar[Tuple[str, str, str, str]] = (
        STOCK_IN,
        STOCK_OUT,
        PURCHASE,
        ADJUSTMENT,
    )


class Transaction:

    transaction_id: str
    product_id: str
    tx_type: str
    quantity: int
    unit_price: float
    supplier_id: str | None
    performed_by: str
    note: str
    timestamp: str

    def __init__(
        self,
        product_id: str,
        tx_type: str,
        quantity: int,
        unit_price: float = 0.0,
        supplier_id: str | None = None,
        performed_by: str = "system",
        note: str = "",
        transaction_id: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        if tx_type not in TransactionType.ALL_TYPES:
            raise ValueError(f"Unsupported transaction type: {tx_type}")
        self.transaction_id = transaction_id or str(uuid.uuid4())
        self.product_id = product_id
        self.tx_type = tx_type
        self.quantity = int(quantity)
        self.unit_price = float(unit_price)
        self.supplier_id = supplier_id
        self.performed_by = performed_by
        self.note = note
        self.timestamp = timestamp or datetime.now().isoformat(timespec="seconds")

    def total_value(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "product_id": self.product_id,
            "tx_type": self.tx_type,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "supplier_id": self.supplier_id,
            "performed_by": self.performed_by,
            "note": self.note,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        return cls(
            product_id=str(data["product_id"]),
            tx_type=str(data["tx_type"]),
            quantity=int(data.get("quantity", 0)),
            unit_price=float(data.get("unit_price", 0.0)),
            supplier_id=data.get("supplier_id"),
            performed_by=str(data.get("performed_by", "system")),
            note=str(data.get("note", "")),
            transaction_id=data.get("transaction_id"),
            timestamp=data.get("timestamp"),
        )

    def __repr__(self) -> str:
        return f"<Transaction {self.tx_type} qty={self.quantity} product={self.product_id}>"
