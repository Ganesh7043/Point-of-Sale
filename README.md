# Simple POS

A minimal point-of-sale system for a small retail/textile shop, built with Flask and SQLite.

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python run.py` (or double-click `START_SERVER.bat` on Windows)
3. Open http://127.0.0.1:5000

## Portals

| Portal | URL | Who |
|--------|-----|-----|
| Admin | http://127.0.0.1:5000/admin | Manage products, view sales |
| Billing | http://127.0.0.1:5000/billing | Search products, cart, checkout |

## Default Users

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin (both portals) |
| staff1 | staff123 | Staff (billing only) |

## Features

- **Login**: branded sign-in page with role-based access (admin sees both portals, staff sees billing only)
- **Dashboard**: KPI cards (products, sales today, revenue, low stock, customers, refunds), best-sellers chart
- **Products**: add / edit / delete with stock status pills (in stock / low / out)
- **Billing**: searchable product grid, cart with quantity controls, customer picker (add new inline),
  cash/card/UPI payments with cash-received and change calculation, printable receipt with shop details
- **Customers**: customer database, per-customer purchase totals, linked to sales
- **Staff**: create/edit/delete user accounts, roles, password resets (last-admin protected)
- **Sales history**: search, sale detail popup, status tracking (completed / partially returned / returned)
- **Returns**: full or partial refunds per item, stock automatically restored, refund history per sale
- **Reports**: today / 7 / 30 / 90-day views, revenue-by-day and top-product charts, CSV export
- **Settings**: shop name, address and phone shown on receipts and reports
- Toast notifications, Esc closes dialogs, responsive layout

## Tech

- **Backend**: Python 3 + Flask (one routes file)
- **Database**: SQLite file `pos_database.db`, created and seeded automatically on first run
- **Frontend**: one stylesheet + three HTML templates, plain JavaScript
