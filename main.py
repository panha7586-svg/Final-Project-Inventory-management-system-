from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path
from typing import Any, Optional

from config import settings
from logger import setup_logger
from models.user import Role
from services.auth_service import AuthService
from services.inventory_service import (
    DuplicateSKUError,
    InsufficientStockError,
    InventoryService,
    ProductNotFoundError,
)
from services.report_service import ReportService
from services.supplier_service import SupplierNotFoundError, SupplierService
from utils import cli_ui
from utils.batch_utils import batch_adjust_stock, import_products_from_csv
from utils.export_utils import export_products_to_csv, export_transactions_to_csv
from utils.validators import (
    CancelInput,
    password_strength_message,
    prompt_choice,
    prompt_confirm,
    prompt_float,
    prompt_int,
    prompt_menu_choice,
    prompt_nonempty_str,
    prompt_optional_str,
)

logger = setup_logger(settings.log_level)

APP_TITLE = "Inventory Management System"
APP_SUBTITLE = "Void Corporation Co. Ltd."


class InventoryApp:

    def __init__(self) -> None:
        self.auth = AuthService()
        self.inventory = InventoryService()
        self.suppliers = SupplierService()
        self.reports = ReportService(self.inventory, self.suppliers)

    def run(self) -> None:
    
        cli_ui.clear_screen()
        cli_ui.print_banner(APP_TITLE, APP_SUBTITLE)
        logger.info("Application started.")

        if not cli_ui.is_rich_available():
            cli_ui.print_warning("Rich is not installed; using the logger/tabulate fallback.")

        if not self.auth.list_users():
            self._create_first_admin()

        if not self._login_loop():
            cli_ui.print_info("Exiting. Goodbye!")
            return
        self._main_menu_loop()

    def _create_first_admin(self) -> None:
        cli_ui.print_warning("No users found. Creating the configured first Admin account.")
        username = settings.default_admin_username.strip()
        password = settings.default_admin_password
        try:
            user = self.auth.create_user(username, password, Role.ADMIN)
        except ValueError as exc:
            cli_ui.print_error(str(exc))
            cli_ui.print_info(
                "Set DEFAULT_ADMIN_USERNAME and a strong DEFAULT_ADMIN_PASSWORD in .env, then run again."
            )
            raise
        cli_ui.print_success(f"Admin account '{user.username}' created. Default password is configured in .env.")
        logger.warning("First-run Admin account created from environment defaults.")

    def _login_loop(self) -> bool:
        attempts = 0
        while not self.auth.is_authenticated():
            cli_ui.print_info(
                f"Login — failed attempts {attempts}/{settings.max_login_attempts}. "
                "Type 'exit' as username to quit."
            )
            username = input("Username: ").strip()
            if username.lower() == "exit":
                return False
            password = input("Password: ").strip()
            if self.auth.login(username, password):
                user = self.auth.current_user
                if user:
                    cli_ui.print_success(f"Welcome, {user.username} ({user.role})!")
                return True
            attempts += 1
            if attempts >= settings.max_login_attempts:
                cli_ui.print_error("Too many failed attempts. Exiting for security.")
                logger.warning("Login lockout reached after %s attempts.", attempts)
                return False
        return True

    def _require_admin(self) -> bool:
        if not self.auth.is_admin():
            cli_ui.print_error("Access denied. This action requires Admin privileges.")
            cli_ui.pause()
            return False
        return True

    def _main_menu_loop(self) -> None:
  
        options = {
            "1": "Product Management",
            "2": "Supplier Management",
            "3": "Stock Movements",
            "4": "Reports & Analytics",
            "5": "Data Export",
            "6": "Batch Operations",
            "7": "User Management (Admin only)",
            "8": "Logout",
            "0": "Exit application",
        }
        while True:
            cli_ui.clear_screen()
            user_label = (
                f"Logged in as: {self.auth.current_user.username} ({self.auth.current_user.role})"
                if self.auth.current_user else "Not authenticated"
            )
            cli_ui.print_banner(APP_TITLE, user_label)
            cli_ui.print_menu("MAIN MENU", options)
            choice = prompt_menu_choice("Select an option", set(options))
            try:
                if choice == "1":
                    self._product_menu()
                elif choice == "2":
                    self._supplier_menu()
                elif choice == "3":
                    self._stock_menu()
                elif choice == "4":
                    self._reports_menu()
                elif choice == "5":
                    self._export_menu()
                elif choice == "6":
                    self._batch_menu()
                elif choice == "7":
                    self._user_menu()
                elif choice == "8":
                    self.auth.logout()
                    if not self._login_loop():
                        return
                elif choice == "0":
                    logger.info("Application exit requested by user.")
                    cli_ui.print_info("Exiting. Goodbye!")
                    return
            except (CancelInput,) as exc:
                logger.info("User cancelled operation: %s", exc)
                cli_ui.print_warning("Cancelled.")
                cli_ui.pause()
            except Exception as exc:  # last-resort boundary for CLI robustness
                logger.exception("Unexpected application error.")
                cli_ui.print_error(f"Unexpected error: {exc}")
                cli_ui.pause()

    # ------------------------------------------------------------------
    # Product management
    # ------------------------------------------------------------------
    def _product_menu(self) -> None:
        options = {
            "1": "List all products",
            "2": "Enhanced search / filtering",
            "3": "Add product (Admin)",
            "4": "Edit product (Admin)",
            "5": "Soft delete product (Admin)",
            "6": "Hard delete product (Admin)",
            "7": "Low-stock / out-of-stock alerts",
            "0": "Back",
        }
        while True:
            cli_ui.print_menu("PRODUCT MANAGEMENT", options)
            choice = prompt_menu_choice("Select an option", set(options))
            try:
                if choice == "1":
                    self._list_products(self.inventory.get_all_products(include_inactive=True))
                    cli_ui.pause()
                elif choice == "2":
                    self._search_products()
                    cli_ui.pause()
                elif choice == "3":
                    if self._require_admin():
                        self._add_product()
                    cli_ui.pause()
                elif choice == "4":
                    if self._require_admin():
                        self._edit_product()
                    cli_ui.pause()
                elif choice == "5":
                    if self._require_admin():
                        self._soft_delete_product()
                    cli_ui.pause()
                elif choice == "6":
                    if self._require_admin():
                        self._hard_delete_product()
                    cli_ui.pause()
                elif choice == "7":
                    self._low_stock_report()
                    cli_ui.pause()
                else:
                    return
            except CancelInput:
                cli_ui.print_warning("Cancelled.")
                cli_ui.pause()

    def _list_products(self, products: list[Any]) -> None:
        columns = ["SKU", "Name", "Category", "Qty", "Cost", "Price", "Reorder", "Status"]
        rows: list[list[Any]] = []
        styles: list[str] = []
        for product in products:
            if not product.active:
                status, style = "Inactive", "grey50"
            elif product.is_out_of_stock():
                status, style = "OUT OF STOCK", "bold red"
            elif product.is_low_stock():
                status, style = "LOW STOCK", "bold yellow"
            else:
                status, style = "OK", "green"
            rows.append([
                product.sku,
                product.name,
                product.category,
                product.quantity,
                f"${product.cost_price:.2f}",
                f"${product.selling_price:.2f}",
                product.reorder_level,
                status,
            ])
            styles.append(style)
        cli_ui.print_table("Products", columns, rows, row_styles=styles)

    def _search_products(self) -> None:
        keyword = input("Keyword (blank for any): ").strip()
        min_price = self._prompt_optional_float("Minimum selling price")
        max_price = self._prompt_optional_float("Maximum selling price")
        min_stock = self._prompt_optional_int("Minimum stock")
        max_stock = self._prompt_optional_int("Maximum stock")
        try:
            results = self.inventory.search_products(
                keyword=keyword,
                min_price=min_price,
                max_price=max_price,
                min_stock=min_stock,
                max_stock=max_stock,
            )
        except ValueError as exc:
            cli_ui.print_error(str(exc))
            return
        self._list_products(results)

    @staticmethod
    def _prompt_optional_float(label: str) -> Optional[float]:
        raw = input(f"{label} [blank = any]: ").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            logger.warning("Invalid optional number entered for %s.", label)
            cli_ui.print_error(f"Invalid number for {label}.")
            return None

    @staticmethod
    def _prompt_optional_int(label: str) -> Optional[int]:
        raw = input(f"{label} [blank = any]: ").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            logger.warning("Invalid optional integer entered for %s.", label)
            cli_ui.print_error(f"Invalid whole number for {label}.")
            return None

    def _pick_supplier_id_optional(self) -> Optional[str]:
        suppliers = self.suppliers.get_all_suppliers()
        if not suppliers or not prompt_confirm("Link this product to a supplier?"):
            return None
        self._list_suppliers(suppliers)
        supplier_id = prompt_nonempty_str("Full Supplier ID")
        try:
            self.suppliers.get_supplier_by_id(supplier_id)
            return supplier_id
        except SupplierNotFoundError as exc:
            cli_ui.print_error(str(exc))
            return None

    def _add_product(self) -> None:
        cli_ui.print_info("=== Add New Product ===")
        product = self.inventory.add_product(
            name=prompt_nonempty_str("Product name"),
            sku=prompt_nonempty_str("SKU (unique code)"),
            category=prompt_nonempty_str("Category"),
            quantity=prompt_int("Initial quantity", minimum=0),
            cost_price=prompt_float("Cost price", minimum=0),
            selling_price=prompt_float("Selling price", minimum=0),
            supplier_id=self._pick_supplier_id_optional(),
            reorder_level=prompt_int("Reorder level", minimum=0),
        )
        cli_ui.print_success(f"Product '{product.name}' added successfully.")

    def _edit_product(self) -> None:
        product = self.inventory.get_product_by_sku(prompt_nonempty_str("SKU to edit"))
        cli_ui.print_info(f"Editing '{product.name}'. Leave values unchanged to keep them.")
        fields: dict[str, Any] = {
            "name": prompt_optional_str("Name", product.name),
            "category": prompt_optional_str("Category", product.category),
            "sku": prompt_optional_str("SKU", product.sku),
        }
        reorder = input(f"Reorder level [{product.reorder_level}]: ").strip()
        cost = input(f"Cost price [{product.cost_price}]: ").strip()
        sell = input(f"Selling price [{product.selling_price}]: ").strip()
        try:
            if reorder:
                fields["reorder_level"] = int(reorder)
            if cost:
                fields["cost_price"] = float(cost)
            if sell:
                fields["selling_price"] = float(sell)
            updated = self.inventory.update_product(product.product_id, **fields)
            cli_ui.print_success(f"Product '{updated.name}' updated.")
        except (ValueError, DuplicateSKUError) as exc:
            cli_ui.print_error(str(exc))

    def _soft_delete_product(self) -> None:
        product = self.inventory.get_product_by_sku(prompt_nonempty_str("SKU to deactivate"))
        if prompt_confirm(f"Deactivate '{product.name}'?"):
            self.inventory.soft_delete_product(product.product_id)
            cli_ui.print_success(f"Product '{product.name}' deactivated.")

    def _hard_delete_product(self) -> None:
        product = self.inventory.get_product_by_sku(prompt_nonempty_str("SKU to permanently delete"))
        cli_ui.print_warning("Hard delete removes the product record but keeps transaction history.")
        if prompt_confirm(f"Permanently delete '{product.name}'?"):
            self.inventory.hard_delete_product(product.product_id)
            cli_ui.print_success(f"Product '{product.name}' permanently deleted.")

    def _low_stock_report(self) -> None:
        low = self.inventory.get_low_stock_products()
        out = self.inventory.get_out_of_stock_products()
        cli_ui.print_info(f"Low stock: {len(low)} | Out of stock: {len(out)}")
        self._list_products(out + low)

    # ------------------------------------------------------------------
    # Supplier management
    # ------------------------------------------------------------------
    def _supplier_menu(self) -> None:
        options = {
            "1": "List suppliers",
            "2": "Search suppliers",
            "3": "Add supplier (Admin)",
            "4": "Edit supplier (Admin)",
            "5": "Soft delete supplier (Admin)",
            "6": "Hard delete supplier (Admin)",
            "0": "Back",
        }
        while True:
            cli_ui.print_menu("SUPPLIER MANAGEMENT", options)
            choice = prompt_menu_choice("Select an option", set(options))
            try:
                if choice == "1":
                    self._list_suppliers(self.suppliers.get_all_suppliers(include_inactive=True))
                    cli_ui.pause()
                elif choice == "2":
                    self._list_suppliers(self.suppliers.search_suppliers(prompt_nonempty_str("Search keyword")))
                    cli_ui.pause()
                elif choice == "3":
                    if self._require_admin():
                        self._add_supplier()
                    cli_ui.pause()
                elif choice == "4":
                    if self._require_admin():
                        self._edit_supplier()
                    cli_ui.pause()
                elif choice == "5":
                    if self._require_admin():
                        self._soft_delete_supplier()
                    cli_ui.pause()
                elif choice == "6":
                    if self._require_admin():
                        self._hard_delete_supplier()
                    cli_ui.pause()
                else:
                    return
            except CancelInput:
                cli_ui.print_warning("Cancelled.")
                cli_ui.pause()

    @staticmethod
    def _list_suppliers(suppliers: list[Any]) -> None:
        columns = ["ID", "Name", "Contact", "Phone", "Email", "Status"]
        rows = [
            [s.supplier_id[:8], s.name, s.contact_person, s.phone, s.email, "Active" if s.active else "Inactive"]
            for s in suppliers
        ]
        cli_ui.print_table("Suppliers", columns, rows)
        cli_ui.print_info("Use the full Supplier ID for edit/delete operations.")

    def _add_supplier(self) -> None:
        supplier = self.suppliers.add_supplier(
            prompt_nonempty_str("Supplier name"),
            prompt_optional_str("Contact person"),
            prompt_optional_str("Phone"),
            prompt_optional_str("Email"),
            prompt_optional_str("Address"),
        )
        cli_ui.print_success(f"Supplier '{supplier.name}' added. ID: {supplier.supplier_id}")

    def _find_supplier_interactively(self) -> Optional[Any]:
        matches = self.suppliers.search_suppliers(prompt_nonempty_str("Supplier name / keyword"))
        if not matches:
            cli_ui.print_error("No matching suppliers found.")
            return None
        if len(matches) == 1:
            return matches[0]
        self._list_suppliers(matches)
        try:
            return self.suppliers.get_supplier_by_id(prompt_nonempty_str("Full Supplier ID"))
        except SupplierNotFoundError as exc:
            cli_ui.print_error(str(exc))
            return None

    def _edit_supplier(self) -> None:
        supplier = self._find_supplier_interactively()
        if not supplier:
            return
        updated = self.suppliers.update_supplier(
            supplier.supplier_id,
            name=prompt_optional_str("Name", supplier.name),
            contact_person=prompt_optional_str("Contact person", supplier.contact_person),
            phone=prompt_optional_str("Phone", supplier.phone),
            email=prompt_optional_str("Email", supplier.email),
            address=prompt_optional_str("Address", supplier.address),
        )
        cli_ui.print_success(f"Supplier '{updated.name}' updated.")

    def _soft_delete_supplier(self) -> None:
        supplier = self._find_supplier_interactively()
        if supplier and prompt_confirm(f"Deactivate '{supplier.name}'?"):
            self.suppliers.soft_delete_supplier(supplier.supplier_id)
            cli_ui.print_success(f"Supplier '{supplier.name}' deactivated.")

    def _hard_delete_supplier(self) -> None:
        supplier = self._find_supplier_interactively()
        if supplier and prompt_confirm(f"Permanently delete '{supplier.name}'?"):
            self.suppliers.hard_delete_supplier(supplier.supplier_id)
            cli_ui.print_success(f"Supplier '{supplier.name}' permanently deleted.")

    # ------------------------------------------------------------------
    # Stock movements
    # ------------------------------------------------------------------
    def _stock_menu(self) -> None:
        options = {
            "1": "Stock In",
            "2": "Stock Out / Sale",
            "3": "Record Purchase",
            "4": "Product transaction history",
            "0": "Back",
        }
        while True:
            cli_ui.print_menu("STOCK MOVEMENTS", options)
            choice = prompt_menu_choice("Select an option", set(options))
            try:
                if choice == "1":
                    self._stock_in()
                elif choice == "2":
                    self._stock_out()
                elif choice == "3":
                    self._record_purchase()
                elif choice == "4":
                    self._view_product_transactions()
                else:
                    return
                if choice != "0":
                    cli_ui.pause()
            except (CancelInput, ProductNotFoundError) as exc:
                cli_ui.print_error(str(exc) or "Cancelled.")
                cli_ui.pause()

    def _pick_product(self) -> Any:
        return self.inventory.get_product_by_sku(prompt_nonempty_str("Product SKU"))

    def _stock_in(self) -> None:
        product = self._pick_product()
        updated = self.inventory.stock_in(
            product.product_id,
            prompt_int("Quantity to add", minimum=1),
            performed_by=self.auth.current_user.username if self.auth.current_user else "system",
            note=prompt_optional_str("Note", ""),
        )
        cli_ui.print_success(f"'{updated.name}' new quantity: {updated.quantity}")

    def _stock_out(self) -> None:
        product = self._pick_product()
        updated = self.inventory.stock_out(
            product.product_id,
            prompt_int("Quantity to remove", minimum=1),
            performed_by=self.auth.current_user.username if self.auth.current_user else "system",
            note=prompt_optional_str("Note", ""),
        )
        cli_ui.print_success(f"'{updated.name}' new quantity: {updated.quantity}")

    def _record_purchase(self) -> None:
        product = self._pick_product()
        supplier = self._find_supplier_interactively()
        if not supplier:
            return
        updated = self.inventory.record_purchase(
            product.product_id,
            prompt_int("Quantity purchased", minimum=1),
            prompt_float("Unit cost", minimum=0),
            supplier.supplier_id,
            performed_by=self.auth.current_user.username if self.auth.current_user else "system",
            note=prompt_optional_str("Note", ""),
        )
        cli_ui.print_success(
            f"Purchase recorded. '{updated.name}' quantity={updated.quantity}, cost=${updated.cost_price:.2f}"
        )

    def _view_product_transactions(self) -> None:
        product = self._pick_product()
        txs = sorted(
            self.inventory.get_transactions_for_product(product.product_id),
            key=lambda tx: tx.timestamp,
            reverse=True,
        )
        rows = [
            [t.timestamp, t.tx_type, t.quantity, f"${t.unit_price:.2f}", f"${t.total_value():.2f}", t.performed_by, t.note]
            for t in txs
        ]
        cli_ui.print_table("Transaction History", ["Date", "Type", "Qty", "Unit Price", "Total", "By", "Note"], rows)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def _reports_menu(self) -> None:
        options = {
            "1": "Summary dashboard",
            "2": "Low-stock / out-of-stock alerts",
            "3": "Stock-out sales history",
            "4": "Sales / revenue summary",
            "5": "Purchase history",
            "6": "Category breakdown",
            "7": "Product turnover analysis",
            "8": "Supplier spending ranking",
            "9": "Profit analysis",
            "0": "Back",
        }
        while True:
            cli_ui.print_menu("REPORTS & ANALYTICS", options)
            choice = prompt_menu_choice("Select an option", set(options))
            if choice == "1":
                self._show_summary()
            elif choice == "2":
                self._low_stock_report()
            elif choice == "3":
                self._show_stock_out_history()
            elif choice == "4":
                self._show_sales_summary()
            elif choice == "5":
                self._show_purchase_history()
            elif choice == "6":
                self._show_category_breakdown()
            elif choice == "7":
                self._show_turnover()
            elif choice == "8":
                self._show_supplier_spending()
            elif choice == "9":
                self._show_profit()
            else:
                return
            cli_ui.pause()

    def _show_summary(self) -> None:
        summary = self.reports.summary()
        rows = [[key.replace("_", " ").title(), value] for key, value in summary.items()]
        cli_ui.print_table("Summary Dashboard", ["Metric", "Value"], rows)

    def _show_stock_out_history(self) -> None:
        rows: list[list[Any]] = []
        for tx in self.reports.stock_out_history():
            try:
                label = self.inventory.get_product_by_id(tx.product_id).sku
            except ProductNotFoundError:
                label = tx.product_id[:8]
            rows.append([tx.timestamp, label, tx.quantity, f"${tx.unit_price:.2f}", f"${tx.total_value():.2f}", tx.performed_by])
        cli_ui.print_table("Stock-Out Sales History", ["Date", "SKU", "Qty", "Unit Price", "Total", "By"], rows)

    def _show_sales_summary(self) -> None:
        summary = self.reports.sales_revenue_summary()
        cli_ui.print_table("Sales / Revenue Summary", ["Metric", "Value"], [
            ["Total Units Sold", summary["total_units_sold"]],
            ["Total Revenue", f"${summary['total_revenue']:.2f}"],
            ["Transactions", summary["transaction_count"]],
        ])

    def _show_purchase_history(self) -> None:
        rows = []
        for tx in self.reports.purchase_history():
            try:
                label = self.inventory.get_product_by_id(tx.product_id).sku
            except ProductNotFoundError:
                label = tx.product_id[:8]
            rows.append([tx.timestamp, label, tx.tx_type, tx.quantity, f"${tx.unit_price:.2f}", f"${tx.total_value():.2f}", tx.performed_by])
        cli_ui.print_table("Purchase / Stock-In History", ["Date", "SKU", "Type", "Qty", "Unit Price", "Total", "By"], rows)

    def _show_category_breakdown(self) -> None:
        rows = [
            [category, data["count"], data["quantity"], f"${float(data['value']):.2f}"]
            for category, data in self.reports.category_breakdown().items()
        ]
        cli_ui.print_table("Inventory by Category", ["Category", "Products", "Qty", "Value"], rows)

    def _show_turnover(self) -> None:
        rows = [
            [row["sku"], row["product"], row["units_sold"], row["current_stock"], f"{row['turnover_rate'] * 100:.2f}%"]
            for row in self.reports.product_turnover_analysis()
        ]
        cli_ui.print_table("Product Turnover Analysis", ["SKU", "Product", "Sold", "Current Stock", "Turnover Proxy"], rows)
        cli_ui.print_info("Turnover proxy = units sold / (units sold + current stock); historical stock snapshots are not stored.")

    def _show_supplier_spending(self) -> None:
        rows = [
            [row["supplier"], row["units_purchased"], f"${row['spending']:.2f}"]
            for row in self.reports.supplier_spending_ranking()
        ]
        cli_ui.print_table("Supplier Spending Ranking", ["Supplier", "Units", "Spending"], rows)

    def _show_profit(self) -> None:
        data = self.reports.profit_analysis()
        cli_ui.print_table("Profit Analysis", ["Metric", "Value"], [
            ["Units Sold", data["units_sold"]],
            ["Sales Revenue", f"${data['sales_revenue']:.2f}"],
            ["Estimated COGS", f"${data['estimated_cogs']:.2f}"],
            ["Gross Profit", f"${data['gross_profit']:.2f}"],
            ["Gross Margin", f"{data['gross_margin_percent']:.2f}%"],
        ])
        cli_ui.print_info(data["method"] + ".")

    # ------------------------------------------------------------------
    # Export and batch operations
    # ------------------------------------------------------------------
    def _export_menu(self) -> None:
        options = {
            "1": "Export products to CSV",
            "2": "Export transactions to CSV",
            "0": "Back",
        }
        while True:
            cli_ui.print_menu("DATA EXPORT", options)
            choice = prompt_menu_choice("Select an option", set(options))
            try:
                if choice == "1":
                    filename = prompt_nonempty_str("Output CSV filename", allow_cancel=False)
                    path = export_products_to_csv(self.inventory.get_all_products(include_inactive=True), filename)
                    cli_ui.print_success(f"Products exported to {path}")
                    cli_ui.pause()
                elif choice == "2":
                    filename = prompt_nonempty_str("Output CSV filename", allow_cancel=False)
                    path = export_transactions_to_csv(self.inventory.get_all_transactions(), filename)
                    cli_ui.print_success(f"Transactions exported to {path}")
                    cli_ui.pause()
                else:
                    return
            except (OSError, ValueError) as exc:
                cli_ui.print_error(str(exc))
                cli_ui.pause()

    def _batch_menu(self) -> None:
        options = {
            "1": "Import products from CSV",
            "2": "Batch stock adjustment from CSV",
            "0": "Back",
        }
        while True:
            cli_ui.print_menu("BATCH OPERATIONS", options)
            choice = prompt_menu_choice("Select an option", set(options))
            try:
                if choice == "1":
                    path = prompt_nonempty_str("CSV filename", allow_cancel=False)
                    result = import_products_from_csv(path, self.inventory)
                    cli_ui.print_success(f"Imported {result['count']} product(s).")
                    for error in result["errors"]:
                        cli_ui.print_warning(error)
                    cli_ui.pause()
                elif choice == "2":
                    path = Path(prompt_nonempty_str("Adjustment CSV filename", allow_cancel=False))
                    with path.open("r", newline="", encoding="utf-8-sig") as handle:
                        reader = csv.DictReader(handle)
                        result = batch_adjust_stock(reader, self.inventory)
                    cli_ui.print_success(f"Adjusted {result['count']} product(s).")
                    for error in result["errors"]:
                        cli_ui.print_warning(error)
                    cli_ui.pause()
                else:
                    return
            except (OSError, ValueError) as exc:
                cli_ui.print_error(str(exc))
                cli_ui.pause()

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------
    def _user_menu(self) -> None:
        if not self._require_admin():
            return
        options = {
            "1": "List users",
            "2": "Create user",
            "3": "Deactivate user",
            "4": "Reactivate user",
            "5": "Reset user password",
            "0": "Back",
        }
        while True:
            cli_ui.print_menu("USER MANAGEMENT", options)
            choice = prompt_menu_choice("Select an option", set(options))
            try:
                if choice == "1":
                    users = self.auth.list_users()
                    rows = [[u.username, u.role, "Active" if u.active else "Inactive", u.created_at] for u in users]
                    cli_ui.print_table("Users", ["Username", "Role", "Status", "Created"], rows)
                    cli_ui.pause()
                elif choice == "2":
                    self._create_user()
                    cli_ui.pause()
                elif choice in {"3", "4"}:
                    username = prompt_nonempty_str("Username")
                    ok = self.auth.deactivate_user(username) if choice == "3" else self.auth.reactivate_user(username)
                    cli_ui.print_success("User updated.") if ok else cli_ui.print_error("User not found.")
                    cli_ui.pause()
                elif choice == "5":
                    username = prompt_nonempty_str("Username")
                    password = prompt_nonempty_str("New password", allow_cancel=False)
                    try:
                        if self.auth.change_password(username, password):
                            cli_ui.print_success("Password updated.")
                        else:
                            cli_ui.print_error("User not found.")
                    except ValueError as exc:
                        cli_ui.print_error(str(exc))
                    cli_ui.pause()
                else:
                    return
            except CancelInput:
                cli_ui.print_warning("Cancelled.")
                cli_ui.pause()

    def _create_user(self) -> None:
        username = prompt_nonempty_str("New username")
        password = prompt_nonempty_str("New password", allow_cancel=False)
        role = prompt_choice("Role", [Role.ADMIN, Role.STAFF])
        if password_strength_message(password):
            cli_ui.print_warning("Password does not meet the strength rules; it will be rejected.")
        try:
            user = self.auth.create_user(username, password, role)
            cli_ui.print_success(f"User '{user.username}' created with role '{user.role}'.")
        except ValueError as exc:
            cli_ui.print_error(str(exc))


def main() -> None:
    try:
        InventoryApp().run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting gracefully.")
        cli_ui.print_info("Interrupted. Goodbye!")
    except Exception as exc:
        logger.exception("Fatal error during application startup.")
        cli_ui.print_error(f"A fatal error occurred: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
