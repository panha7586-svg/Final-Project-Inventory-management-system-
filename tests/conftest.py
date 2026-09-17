
from __future__ import annotations

import pytest

from config import Settings
from services.inventory_service import InventoryService
from services.supplier_service import SupplierService


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        max_login_attempts=3,
        password_min_length=8,
        default_admin_username="admin",
        default_admin_password="Admin123!",
        low_stock_threshold=10,
        log_level="WARNING",
    )


@pytest.fixture
def inventory(test_settings: Settings) -> InventoryService:
    return InventoryService(test_settings)


@pytest.fixture
def suppliers(test_settings: Settings) -> SupplierService:
    return SupplierService(test_settings)
