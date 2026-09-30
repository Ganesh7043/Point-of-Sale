import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')

# Default catalogue seeded on first run
SUPERMARKET_PRODUCTS = [
    # Fruits & vegetables
    ('Tomato (1 kg)', 40, 60),
    ('Onion (1 kg)', 35, 80),
    ('Potato (1 kg)', 30, 90),
    ('Banana (dozen)', 60, 30),
    ('Apple Shimla (1 kg)', 180, 25),
    ('Orange (1 kg)', 90, 35),
    ('Carrot (500 g)', 30, 40),
    ('Spinach (bunch)', 15, 20),
    ('Capsicum Green (500 g)', 40, 25),
    ('Lemon (4 pcs)', 20, 30),
    # Dairy & eggs
    ('Amul Milk 500 ml', 27, 50),
    ('Amul Butter 100 g', 56, 30),
    ('Paneer 200 g', 90, 20),
    ('Curd 400 g', 40, 35),
    ('Eggs (6 pcs)', 45, 40),
    ('Cheese Slices (10 pcs)', 135, 25),
    # Staples
    ('Basmati Rice 5 kg', 550, 40),
    ('Aashirvaad Atta 5 kg', 240, 45),
    ('Toor Dal 1 kg', 160, 50),
    ('Sugar 1 kg', 45, 60),
    ('Sunflower Oil 1 L', 140, 55),
    ('Iodised Salt 1 kg', 25, 70),
    ('Wheat Bread 400 g', 45, 30),
    # Snacks & beverages
    ('Parle-G Biscuits', 10, 100),
    ("Lay's Classic 52 g", 20, 80),
    ('Britannia Good Day 100 g', 30, 60),
    ('Maggi Noodles 4-pack', 56, 70),
    ('Tata Tea Premium 500 g', 260, 30),
    ('Nescafe Classic 50 g', 165, 25),
    ('Coca-Cola 750 ml', 40, 60),
    ('Real Mixed Fruit Juice 1 L', 110, 35),
    ('Bisleri Water 1 L', 20, 90),
    # Personal care & household
    ('Colgate Toothpaste 100 g', 60, 40),
    ('Lifebuoy Soap 125 g', 35, 50),
    ('Dettol Handwash 200 ml', 85, 30),
    ('Surf Excel 1 kg', 140, 35),
    ('Vim Dishwash Bar', 20, 60),
    ('Harpic Toilet Cleaner 500 ml', 95, 25),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables, migrate older databases, and seed sample data on first run."""
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff'
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            customer_name TEXT DEFAULT '',
            staff_name TEXT NOT NULL,
            total REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            change_amount REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'cash',
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            quantity_returned INTEGER DEFAULT 0,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        );

        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            staff_name TEXT NOT NULL,
            refund_total REAL NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    ''')

    # --- migrations for databases created by older versions ---
    existing = {r[1] for r in c.execute("PRAGMA table_info(transactions)")}
    for col, ddl in [
        ('customer_id', 'INTEGER'),
        ('paid_amount', "REAL DEFAULT 0"),
        ('change_amount', "REAL DEFAULT 0"),
        ('status', "TEXT DEFAULT 'completed'"),
    ]:
        if col not in existing:
            c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {ddl}")

    existing = {r[1] for r in c.execute("PRAGMA table_info(transaction_items)")}
    if 'quantity_returned' not in existing:
        c.execute("ALTER TABLE transaction_items ADD COLUMN quantity_returned INTEGER DEFAULT 0")
    if 'product_id' not in existing:
        c.execute("ALTER TABLE transaction_items ADD COLUMN product_id INTEGER")

    # --- seed sample data on first run ---
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash
        c.executemany(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            [
                ('admin', generate_password_hash('admin123'), 'Admin', 'admin'),
                ('staff1', generate_password_hash('staff123'), 'Staff One', 'staff'),
            ]
        )
        c.executemany(
            "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
            SUPERMARKET_PRODUCTS
        )
        c.executemany(
            "INSERT INTO customers (name, phone) VALUES (?, ?)",
            [
                ('Walk-in Customer', ''),
                ('Meera Nair', '9845001234'),
                ('Sunita Verma', '9712345678'),
            ]
        )
        c.executemany(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            [('shop_name', 'Simple POS'), ('shop_address', ''), ('shop_phone', '')]
        )

    conn.commit()
    conn.close()


def next_invoice_no(conn):
    """Generate the next invoice number, e.g. INV-20260930-0001."""
    date_part = datetime.now().strftime('%Y%m%d')
    row = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE invoice_no LIKE ?",
        (f'INV-{date_part}-%',)
    ).fetchone()
    return f'INV-{date_part}-{row[0] + 1:04d}'


def get_setting(db, key, default=''):
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def get_settings(db):
    return {r[0]: r[1] for r in db.execute("SELECT key, value FROM settings")}
