"""Seed the SQLite database with sample product and order data.

Creates data/products.db with products and orders tables.
Account names match Salesforce Developer Edition sample data.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "products.db"

PRODUCTS = [
    (1, "Samuel Adams Boston Lager", "Craft Lager", "Samuel Adams"),
    (2, "Sam Adams Seasonal Variety", "Variety Pack", "Samuel Adams"),
    (3, "Angry Orchard Crisp Apple", "Hard Cider", "Angry Orchard"),
    (4, "Truly Wild Berry", "Hard Seltzer", "Truly"),
    (5, "Truly Lemonade Variety", "Hard Seltzer", "Truly"),
    (6, "Dogfish Head 60 Minute IPA", "IPA", "Dogfish Head"),
    (7, "Twisted Tea Original", "Hard Tea", "Twisted Tea"),
    (8, "Samuel Adams OctoberFest", "Seasonal Lager", "Samuel Adams"),
]

# Account names from SF Developer Edition sample data
ORDERS = [
    (1001, "Edge Communications", "Samuel Adams Boston Lager", 48, "2025-09-15"),
    (1002, "Edge Communications", "Truly Wild Berry", 120, "2025-10-03"),
    (1003, "Edge Communications", "Angry Orchard Crisp Apple", 36, "2026-01-20"),
    (1004, "Burlington Textiles Corp of America", "Twisted Tea Original", 72, "2025-08-22"),
    (1005, "Burlington Textiles Corp of America", "Samuel Adams Boston Lager", 24, "2025-11-10"),
    (1006, "Burlington Textiles Corp of America", "Truly Lemonade Variety", 96, "2026-02-14"),
    (1007, "GenePoint", "Dogfish Head 60 Minute IPA", 60, "2025-10-18"),
    (1008, "GenePoint", "Samuel Adams OctoberFest", 48, "2025-09-30"),
    (1009, "Express Logistics and Transport", "Truly Wild Berry", 144, "2025-12-05"),
    (1010, "Express Logistics and Transport", "Angry Orchard Crisp Apple", 84, "2026-01-15"),
    (1011, "Express Logistics and Transport", "Sam Adams Seasonal Variety", 36, "2026-03-01"),
    (1012, "University of Arizona", "Twisted Tea Original", 200, "2025-11-22"),
    (1013, "University of Arizona", "Truly Lemonade Variety", 180, "2025-12-10"),
    (1014, "University of Arizona", "Samuel Adams Boston Lager", 60, "2026-02-28"),
    (1015, "United Oil & Gas, Corp.", "Dogfish Head 60 Minute IPA", 48, "2025-10-08"),
    (1016, "United Oil & Gas, Corp.", "Samuel Adams OctoberFest", 72, "2025-09-20"),
    (1017, "United Oil & Gas, Corp.", "Truly Wild Berry", 96, "2026-01-30"),
    (1018, "sForce", "Samuel Adams Boston Lager", 24, "2025-11-05"),
    (1019, "sForce", "Angry Orchard Crisp Apple", 36, "2026-02-18"),
    (1020, "Pyramid Construction Inc.", "Twisted Tea Original", 48, "2025-12-20"),
    (1021, "Pyramid Construction Inc.", "Truly Lemonade Variety", 60, "2026-03-10"),
    (1022, "Dickenson plc", "Dogfish Head 60 Minute IPA", 30, "2025-10-25"),
    (1023, "Dickenson plc", "Sam Adams Seasonal Variety", 24, "2026-01-08"),
    (1024, "Grand Hotels & Resorts Ltd", "Samuel Adams Boston Lager", 120, "2025-11-15"),
    (1025, "Grand Hotels & Resorts Ltd", "Angry Orchard Crisp Apple", 96, "2026-02-05"),
]


def seed():
    """Create and populate the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing DB so we start fresh
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            brand_family TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            account_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity_cases INTEGER NOT NULL,
            order_date TEXT NOT NULL
        )
    """)

    cur.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)",
        PRODUCTS,
    )
    cur.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        ORDERS,
    )

    conn.commit()
    conn.close()
    print(f"Database seeded at {DB_PATH} — {len(PRODUCTS)} products, {len(ORDERS)} orders")


if __name__ == "__main__":
    seed()
