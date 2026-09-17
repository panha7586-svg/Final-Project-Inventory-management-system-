
from __future__ import annotations

from services.report_service import ReportService


def test_standard_and_advanced_reports(inventory, suppliers) -> None:
    supplier_a = suppliers.add_supplier("Supplier A")
    supplier_b = suppliers.add_supplier("Supplier B")

    laptop = inventory.add_product("Laptop", "L-1", "Laptop", 10, 500, 800, supplier_a.supplier_id)
    mouse = inventory.add_product("Mouse", "M-1", "Accessory", 20, 10, 25, supplier_b.supplier_id)

    inventory.stock_out(laptop.product_id, 4, unit_price=800)
    inventory.record_purchase(mouse.product_id, 100, 20, supplier_b.supplier_id)
    inventory.record_purchase(laptop.product_id, 2, 480, supplier_a.supplier_id)

    reports = ReportService(inventory, suppliers)

    sales = reports.sales_revenue_summary()
    assert sales["total_units_sold"] == 4
    assert sales["total_revenue"] == 3200.0

    turnover = reports.product_turnover_analysis()
    assert turnover[0]["sku"] == "L-1"
    assert turnover[0]["units_sold"] == 4
    assert turnover[0]["turnover_rate"] > 0

    spending = reports.supplier_spending_ranking()
    assert spending[0]["supplier"] == "Supplier B"
    assert spending[0]["spending"] == 2000.0

    profit = reports.profit_analysis()
    assert profit["sales_revenue"] == 3200.0
    assert profit["estimated_cogs"] == 1920.0
    assert profit["gross_profit"] == 1280.0
    assert profit["gross_margin_percent"] == 40.0
    assert "current cost_price" in profit["method"]


def test_reports_handle_no_transactions(inventory, suppliers) -> None:
    reports = ReportService(inventory, suppliers)
    assert reports.sales_revenue_summary() == {
        "total_units_sold": 0,
        "total_revenue": 0.0,
        "transaction_count": 0,
    }
    assert reports.product_turnover_analysis() == []
    assert reports.supplier_spending_ranking() == []
    profit = reports.profit_analysis()
    assert profit["gross_profit"] == 0.0
    assert profit["gross_margin_percent"] == 0.0
