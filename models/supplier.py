
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict


class Supplier:

    supplier_id: str
    name: str
    contact_person: str
    phone: str
    email: str
    address: str
    active: bool
    created_at: str

    def __init__(
        self,
        name: str,
        contact_person: str = "",
        phone: str = "",
        email: str = "",
        address: str = "",
        supplier_id: str | None = None,
        active: bool = True,
        created_at: str | None = None,
    ) -> None:
        self.supplier_id = supplier_id or str(uuid.uuid4())
        self.name = name
        self.contact_person = contact_person
        self.phone = phone
        self.email = email
        self.address = address
        self.active = bool(active)
        self.created_at = created_at or datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supplier_id": self.supplier_id,
            "name": self.name,
            "contact_person": self.contact_person,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "active": self.active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Supplier":
        return cls(
            name=str(data["name"]),
            contact_person=str(data.get("contact_person", "")),
            phone=str(data.get("phone", "")),
            email=str(data.get("email", "")),
            address=str(data.get("address", "")),
            supplier_id=data.get("supplier_id"),
            active=bool(data.get("active", True)),
            created_at=data.get("created_at"),
        )

    def __repr__(self) -> str:
        return f"<Supplier {self.name}>"
