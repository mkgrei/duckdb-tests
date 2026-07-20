"""Generate the sample datasets the playground queries against.

Two files, two formats, on purpose:
  - data/sales.csv        -> ingested into a real DuckDB table (tour step 1)
  - data/products.parquet -> queried in place, never imported (tour step 2)
"""

import csv
import datetime
import random
from pathlib import Path

import duckdb

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SALES_CSV = DATA_DIR / "sales.csv"
PRODUCTS_PARQUET = DATA_DIR / "products.parquet"

N_SALES = 5000
N_PRODUCTS = 50

CATEGORIES = ["Electronics", "Home", "Toys", "Books", "Grocery"]
REGIONS = ["NA", "EMEA", "APAC", "LATAM"]

ADJECTIVES = ["Aero", "Blue", "Compact", "Deluxe", "Eco", "Flex", "Giga", "Hyper", "Ion", "Jet"]
NOUNS = ["Widget", "Gadget", "Lamp", "Speaker", "Blender", "Puzzle", "Novel", "Snack", "Charger", "Chair"]


def _generate_products(rng: random.Random) -> list[dict]:
    products = []
    for pid in range(1, N_PRODUCTS + 1):
        products.append(
            {
                "product_id": pid,
                "product_name": f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)} {pid}",
                "category": rng.choice(CATEGORIES),
                "price": round(rng.uniform(3.0, 400.0), 2),
            }
        )
    return products


def generate(force: bool = False) -> None:
    """Create sales.csv and products.parquet. Idempotent unless force=True."""
    DATA_DIR.mkdir(exist_ok=True)
    if not force and SALES_CSV.exists() and PRODUCTS_PARQUET.exists():
        return

    rng = random.Random(42)
    products = _generate_products(rng)
    price_by_id = {p["product_id"]: p["price"] for p in products}

    start = datetime.date(2024, 1, 1)
    span_days = 730  # 2024-2025
    with SALES_CSV.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["order_id", "order_date", "region", "product_id", "quantity", "amount", "customer_id"]
        )
        for order_id in range(1, N_SALES + 1):
            product_id = rng.randint(1, N_PRODUCTS)
            quantity = rng.randint(1, 10)
            jitter = rng.uniform(0.9, 1.1)  # discounts / taxes
            writer.writerow(
                [
                    order_id,
                    start + datetime.timedelta(days=rng.randrange(span_days)),
                    rng.choice(REGIONS),
                    product_id,
                    quantity,
                    round(price_by_id[product_id] * quantity * jitter, 2),
                    rng.randint(1, 800),
                ]
            )

    # Let DuckDB itself write the Parquet file — no pyarrow needed.
    con = duckdb.connect()
    con.execute(
        "CREATE TEMP TABLE products (product_id INTEGER, product_name VARCHAR, category VARCHAR, price DOUBLE)"
    )
    con.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)",
        [(p["product_id"], p["product_name"], p["category"], p["price"]) for p in products],
    )
    con.execute(f"COPY products TO '{PRODUCTS_PARQUET}' (FORMAT PARQUET)")
    con.close()


if __name__ == "__main__":
    generate(force=True)
    print(f"wrote {SALES_CSV} and {PRODUCTS_PARQUET}")
