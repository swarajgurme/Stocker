#!/usr/bin/env python3
"""
Fill sparse sales history so forecasting works for every store × product combo.

Ensures at least N unique sale_date rows per pair within a date window
(default: 2023-01-01 through 2024-12-31, matching the Forecast page defaults).
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from database import check_db_connection, get_db_session  # noqa: E402
from models import Product, Sale, Store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MIN = 30
DEFAULT_START = date(2023, 1, 1)
DEFAULT_END = date(2024, 12, 31)
BATCH_SIZE = 500


def _date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def fill_history(
    min_records: int = DEFAULT_MIN,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
    seed: int = 7,
) -> int:
    if not check_db_connection():
        raise RuntimeError("Database unavailable. Check DATABASE_URL.")

    rng = random.Random(seed)
    all_dates = _date_range(start, end)
    inserted = 0

    with get_db_session() as db:
        stores = db.query(Store).filter_by(is_active=True).all()
        products = db.query(Product).filter_by(is_active=True).all()

        pending: list[dict] = []

        for store in stores:
            for product in products:
                existing = {
                    row.sale_date
                    for row in db.query(Sale.sale_date)
                    .filter(
                        Sale.store_id == store.id,
                        Sale.product_id == product.id,
                        Sale.sale_date.between(start, end),
                    )
                    .all()
                }
                need = max(0, min_records - len(existing))
                if need == 0:
                    continue

                available = [d for d in all_dates if d not in existing]
                rng.shuffle(available)
                pick = available[:need]

                base_price = float(product.selling_price or 50.0)
                for sale_date in pick:
                    qty = max(1, int(rng.gauss(2.5, 1.0)))
                    revenue = round(base_price * qty * rng.uniform(0.9, 1.15), 2)
                    ewma = round(revenue * rng.uniform(0.92, 1.08), 2)
                    pending.append(
                        {
                            "store_id": store.id,
                            "product_id": product.id,
                            "sale_date": sale_date,
                            "year": sale_date.year,
                            "quarter": (sale_date.month - 1) // 3 + 1,
                            "day_of_week": sale_date.weekday(),
                            "quantity": qty,
                            "revenue": revenue,
                            "ewma": ewma,
                            "created_at": datetime.utcnow(),
                        }
                    )

                if len(pending) >= BATCH_SIZE:
                    db.bulk_insert_mappings(Sale, pending)
                    inserted += len(pending)
                    pending.clear()
                    logger.info("Inserted %s rows so far...", inserted)

        if pending:
            db.bulk_insert_mappings(Sale, pending)
            inserted += len(pending)

        db.commit()

    logger.info("Added %s historical sales rows (%s to %s)", inserted, start, end)
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill forecast history gaps")
    parser.add_argument("--min", type=int, default=DEFAULT_MIN, help="Min records per store×product")
    parser.add_argument("--start", default="2023-01-01", help="Window start (YYYY-MM-DD)")
    parser.add_argument("--end", default="2024-12-31", help="Window end (YYYY-MM-DD)")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    fill_history(min_records=args.min, start=start, end=end, seed=args.seed)
    print(f"Done. Ensured >= {args.min} sales per store×product between {start} and {end}.")


if __name__ == "__main__":
    main()
