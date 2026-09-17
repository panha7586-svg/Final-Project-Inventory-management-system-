# Inventory Management System (CLI)

A Python OOP command-line inventory system with JSON persistence, role-based authentication, atomic writes, transaction auditing, reporting, CSV export, advanced search, and batch operations.

## Features

- Admin/Staff authentication with salted SHA-256 password hashes.
- Strong-password enforcement: 8+ characters, uppercase, lowercase, and digit.
- Product and supplier CRUD with soft and hard delete.
- Stock-in, stock-out, purchase, and signed batch adjustment movements.
- Atomic JSON persistence under `data/`.
- Low-stock and out-of-stock alerts.
- Rich terminal interface with Tabulate/plain-text fallback.
- Configurable settings via `.env`.
- Console + `app.log` logging with configurable log level.
- Enhanced product search by keyword, selling-price range, and stock range.
- Product turnover proxy, supplier spending ranking, and gross-profit analysis.
- CSV export for products and transactions.
- CSV product import and CSV batch stock adjustment.
- Pytest coverage for authentication, inventory, reports, validators, export, and batch operations.

## Project structure

```text
.
├── main.py
├── config.py
├── logger.py
├── requirements.txt
├── .env.example
├── README.md
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── product.py
│   ├── supplier.py
│   └── transaction.py
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   ├── inventory_service.py
│   ├── supplier_service.py
│   └── report_service.py
├── utils/
│   ├── __init__.py
│   ├── json_handler.py
│   ├── validators.py
│   ├── cli_ui.py
│   ├── export_utils.py
│   └── batch_utils.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth_service.py
│   ├── test_inventory_service.py
│   ├── test_report_service.py
│   ├── test_validators.py
│   └── test_export_batch.py
└── data/
    ├── users.json
    ├── products.json
    ├── suppliers.json
    └── transactions.json
```

The four `data/*.json` files are backward-compatible with the original repository schema and may be kept unchanged. Missing files are created automatically.

## Setup

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create local configuration:

```bash
copy .env.example .env
```

or on macOS/Linux:

```bash
cp .env.example .env
```

Run:

```bash
python main.py
```

On an empty data directory, the configured default Admin account is created automatically. The default example credentials are `admin` / `Admin123!`; change them in `.env` for a real deployment.

## CSV formats

### Product import

Required columns:

```text
name,sku,category,quantity,cost_price,selling_price
```

Optional columns:

```text
supplier_id,reorder_level
```

### Batch stock adjustment

The CSV used by the menu should contain either `sku` or `product_id`, plus a signed `quantity`. Positive values add stock and negative values remove stock.

Example:

```text
sku,quantity,note,performed_by
KEY-1,5,Quarterly count,admin
M-1,-2,Damaged units,admin
```

## Testing

Run the complete test suite:

```bash
pytest
```

All JSON service tests use pytest's `tmp_path` fixture, so normal repository data is not modified by the tests.

## Compatibility notes

The upgraded models retain the original JSON keys and salted SHA-256 representation. Existing `data/users.json`, `products.json`, `suppliers.json`, and `transactions.json` can be reused directly. Existing transaction records remain readable.

Profit analysis is explicitly an estimate because the original data model stores transaction unit prices but does not store historical cost layers. Turnover is a proxy because the original data model does not store daily inventory snapshots.
