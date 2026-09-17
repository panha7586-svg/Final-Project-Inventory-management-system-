from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from models.product import Product
from services.inventory_service import (
    InsufficientStockError,
    InventoryService,
    ProductNotFoundError,
)


def _required(row: Mapping[str, str], key: str) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        raise ValueError(f"Missing required CSV field: {key}")
    return value


def import_products_from_csv(filename: str | Path, inventory_service: InventoryService) -> dict[str, Any]:
   
    imported: list[Product] = []
    errors: list[str] = []

    with Path(filename).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"name", "sku", "category", "quantity", "cost_price", "selling_price"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV must contain: name, sku, category, quantity, cost_price, selling_price")

        for line_number, row in enumerate(reader, start=2):
            try:
                product = inventory_service.add_product(
                    name=_required(row, "name"),
                    sku=_required(row, "sku"),
                    category=_required(row, "category"),
                    quantity=int(_required(row, "quantity")),
                    cost_price=float(_required(row, "cost_price")),
                    selling_price=float(_required(row, "selling_price")),
                    supplier_id=(row.get("supplier_id") or "").strip() or None,
                    reorder_level=int(
                        (row.get("reorder_level") or str(inventory_service.config.low_stock_threshold)).strip()
                    ),
                )
                imported.append(product)
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(f"Line {line_number}: {exc}")

    return {"imported": imported, "count": len(imported), "errors": errors}


def batch_adjust_stock(
    adjustments: Iterable[Mapping[str, Any]],
    inventory_service: InventoryService,
) -> dict[str, Any]:
    results: list[Product] = []
    errors: list[str] = []

    for index, adjustment in enumerate(adjustments, start=1):
        try:
            identifier = str(adjustment.get("product_id") or adjustment.get("sku") or "").strip()
            if not identifier:
                raise ValueError("product_id or sku is required")
            delta = int(adjustment["quantity"])
            note = str(adjustment.get("note", "Batch stock adjustment"))
            performed_by = str(adjustment.get("performed_by", "system"))
            product = inventory_service.adjust_stock(
                identifier, delta, performed_by=performed_by, note=note
            )
            results.append(product)
        except (ValueError, TypeError, KeyError, ProductNotFoundError, InsufficientStockError) as exc:
            errors.append(f"Adjustment {index}: {exc}")

    return {"adjusted": results, "count": len(results), "errors": errors}
