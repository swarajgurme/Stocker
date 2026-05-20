#!/usr/bin/env python3
"""
Bulk seed script for Stocker — generates realistic demo data for dashboards,
analytics, forecasting, inventory, and anomaly features.

Default: 10,000 sales rows plus supporting master/derived records.
Uses batch inserts for performance. Safe to re-run with --replace.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import func  # noqa: E402

import bcrypt  # noqa: E402
from database import (  # noqa: E402
    check_db_connection,
    engine,
    get_db_session,
    init_db,
)
from models import (  # noqa: E402
    AlertSeverity,
    AlertType,
    Anomaly,
    AnomalyType,
    AuditLog,
    Cluster,
    Forecast,
    ForecastModelType,
    ForecastValue,
    InventoryAlert,
    InventoryLevel,
    Product,
    Recommendation,
    RecommendationType,
    Sale,
    Store,
    User,
    UserRole,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Align with ml_utils/validators.py and CSV migration
STORE_SPECS = [
    ("S001", "Mumbai Central", "West"),
    ("S002", "Delhi North Hub", "North"),
    ("S003", "Chennai South", "South"),
    ("S004", "Kolkata East", "East"),
    ("S005", "Bangalore West", "West"),
]

PRODUCT_SPECS = [
    ("P001", "Air Filter", "Accessories", "Bosch", 12.5, 24.99),
    ("P002", "Alternator", "Electrical", "Denso", 85.0, 149.99),
    ("P003", "Battery", "Electrical", "Exide", 55.0, 99.99),
    ("P004", "Brake Pad", "Breaks", "Brembo", 28.0, 54.99),
    ("P005", "Coolant", "Cooling System", "Castrol", 8.5, 16.99),
    ("P006", "Disc Rotor", "Breaks", "ATE", 42.0, 79.99),
    ("P007", "Engine Oil", "Engine", "Mobil", 18.0, 34.99),
    ("P008", "Fans", "Cooling System", "Valeo", 35.0, 64.99),
    ("P009", "Fuse", "Electrical", "Littelfuse", 2.5, 5.99),
    ("P010", "LED", "Accessories", "Philips", 6.0, 12.99),
    ("P011", "Radiator", "Cooling System", "Nissens", 95.0, 169.99),
    ("P012", "Rearview Mirror", "Accessories", "OEM", 22.0, 44.99),
    ("P013", "Resistors", "Electrical", "Vishay", 1.2, 3.49),
    ("P014", "Sensor", "Electrical", "Bosch", 38.0, 72.99),
    ("P015", "Sideview Mirror", "Accessories", "OEM", 18.0, 36.99),
    ("P016", "Spark Plugs", "Engine", "NGK", 9.0, 18.99),
    ("P017", "Thermostat", "Cooling System", "Wahler", 14.0, 28.99),
    ("P018", "Water Pump", "Engine", "Gates", 48.0, 89.99),
    ("P019", "Windshield", "Accessories", "Pilkington", 120.0, 219.99),
    ("P020", "Wires", "Electrical", "Delphi", 4.5, 9.99),
]

DEMO_USER_SPECS = [
    ("analyst@stocker.demo", "Ava Analyst", UserRole.BUSINESS_ANALYST),
    ("planner@stocker.demo", "Priya Planner", UserRole.SUPPLY_CHAIN_PLANNER),
    ("manager@stocker.demo", "Raj Manager", UserRole.STORE_MANAGER),
    ("exec@stocker.demo", "Elena Executive", UserRole.EXECUTIVE),
]

BATCH_SIZE = 1000
DEFAULT_SALES_COUNT = 10_000
DEFAULT_SEED = 42


def _apply_schema() -> None:
    if os.getenv("SKIP_ALEMBIC", "").lower() == "true":
        init_db()
        return
    ini = backend_dir / "alembic.ini"
    if ini.is_file():
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(ini))
        command.upgrade(cfg, "head")
        logger.info("Alembic schema up to date")
    else:
        init_db()


def _ensure_stores(db) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for code, name, region in STORE_SPECS:
        row = db.query(Store).filter_by(store_code=code).first()
        if not row:
            row = Store(
                store_code=code,
                name=name,
                region=region,
                manager_name=f"{name} Manager",
                city=name.split()[0],
                state=region,
                country="India",
                phone=f"+91-{random.randint(70000, 99999)}{random.randint(10000, 99999)}",
                email=f"{code.lower()}@stocker.demo",
                is_active=True,
            )
            db.add(row)
            db.flush()
        mapping[code] = row.id
    db.commit()
    return mapping


def _ensure_products(db) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for code, name, category, brand, cost, price in PRODUCT_SPECS:
        row = db.query(Product).filter_by(product_code=code).first()
        if not row:
            sku = f"SKU-{code}"
            row = Product(
                product_code=code,
                name=name,
                category=category,
                sku=sku,
                brand=brand,
                unit_cost=cost,
                selling_price=price,
                is_active=True,
            )
            db.add(row)
            db.flush()
        mapping[name] = row.id
    db.commit()
    return mapping


def _clear_transactional_data(db) -> None:
    """Remove rows that will be regenerated; keep stores/products/admin."""
    from models import ForecastValue, ReportOutput, ScheduledReport

    tables = [
        ReportOutput,
        ScheduledReport,
        ForecastValue,
        Forecast,
        InventoryAlert,
        InventoryLevel,
        Cluster,
        Anomaly,
        Recommendation,
        AuditLog,
        Sale,
    ]
    for model in tables:
        deleted = db.query(model).delete(synchronize_session=False)
        logger.info("Cleared %s rows from %s", deleted, model.__tablename__)

    demo_emails = [spec[0] for spec in DEMO_USER_SPECS]
    removed_users = (
        db.query(User)
        .filter(User.email.in_(demo_emails))
        .delete(synchronize_session=False)
    )
    if removed_users:
        logger.info("Removed %s demo users", removed_users)
    db.commit()


def _random_sale_date(rng: random.Random, end: date, span_days: int) -> date:
    offset = rng.randint(0, span_days)
    return end - timedelta(days=offset)


def _build_sales_rows(
    rng: random.Random,
    store_ids: Sequence[int],
    product_meta: Sequence[Tuple[int, float]],
    count: int,
    end_date: date,
    span_days: int,
) -> List[dict]:
    """Generate unique (store, product, date) sales with seasonal variation."""
    used: set[Tuple[int, int, date]] = set()
    rows: List[dict] = []
    attempts = 0
    max_attempts = count * 25

    category_multipliers = {
        "Engine": 1.35,
        "Electrical": 1.2,
        "Breaks": 1.1,
        "Cooling System": 1.0,
        "Accessories": 0.85,
    }

    while len(rows) < count and attempts < max_attempts:
        attempts += 1
        store_id = rng.choice(store_ids)
        product_id, base_price = rng.choice(product_meta)
        sale_date = _random_sale_date(rng, end_date, span_days)
        key = (store_id, product_id, sale_date)
        if key in used:
            continue
        used.add(key)

        month = sale_date.month
        seasonal = 1.0 + 0.15 * ((month - 6) / 6.0)
        qty = max(1, int(rng.gauss(3, 1.2)))
        unit_price = base_price * seasonal * rng.uniform(0.92, 1.12)
        revenue = round(unit_price * qty, 2)
        ewma = round(revenue * rng.uniform(0.88, 1.05), 2)

        rows.append(
            {
                "store_id": store_id,
                "product_id": product_id,
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

    if len(rows) < count:
        raise RuntimeError(
            f"Could only generate {len(rows)} unique sales (requested {count}). "
            "Increase span_days or reduce count."
        )
    return rows


def _bulk_insert_sales(db, rows: List[dict]) -> int:
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i : i + BATCH_SIZE]
        db.bulk_insert_mappings(Sale, chunk)
        db.flush()
        total += len(chunk)
        logger.info("Inserted sales batch: %s / %s", total, len(rows))
    db.commit()
    return total


def _bootstrap_inventory(db, rng: random.Random) -> int:
    cutoff = datetime.utcnow().date() - timedelta(days=365)
    agg = (
        db.query(
            Sale.store_id,
            Sale.product_id,
            func.sum(Sale.quantity).label("tq"),
            func.avg(Sale.ewma).label("avg_sig"),
        )
        .filter(Sale.sale_date >= cutoff)
        .group_by(Sale.store_id, Sale.product_id)
        .all()
    )

    created = 0
    for row in agg:
        exists = (
            db.query(InventoryLevel)
            .filter_by(store_id=row.store_id, product_id=row.product_id)
            .first()
        )
        if exists:
            continue
        qty = int(row.tq or 0)
        sig = float(row.avg_sig or 0)
        current = max(15, min(850, qty * 2 + int(sig % 150)))
        safety = max(20.0, sig * rng.uniform(0.04, 0.08))
        rop = max(35.0, sig * rng.uniform(0.10, 0.16))
        # ~18% low-stock rows so dashboard KPIs and alerts are populated
        force_low = rng.random() < 0.18
        low_stock = force_low or current < safety
        stock_level = max(5, int(safety * 0.35)) if low_stock else current

        lvl = InventoryLevel(
            store_id=row.store_id,
            product_id=row.product_id,
            current_stock=stock_level,
            safety_stock=safety,
            reorder_point=rop,
            lead_time_days=rng.choice([5, 7, 10, 14]),
            last_count_date=datetime.utcnow().date() - timedelta(days=rng.randint(1, 30)),
            last_calculated=datetime.utcnow(),
        )
        db.add(lvl)
        db.flush()
        created += 1

        if low_stock or rng.random() < 0.12:
            alert_type = AlertType.LOW_STOCK if low_stock else rng.choice(
                [AlertType.OVERSTOCK, AlertType.UNDERSTOCK_RISK, AlertType.DEMAND_SPIKE]
            )
            db.add(
                InventoryAlert(
                    inventory_level_id=lvl.id,
                    alert_type=alert_type,
                    severity=rng.choice(list(AlertSeverity)),
                    message=f"{alert_type.value.replace('_', ' ').title()} for store-product pair",
                    current_value=float(lvl.current_stock),
                    threshold_value=float(lvl.safety_stock),
                    is_resolved=rng.random() < 0.25,
                )
            )
    db.commit()
    return created


def _seed_forecasts(db, store_ids: Sequence[int], product_ids: Sequence[int], rng: random.Random) -> int:
    """Create completed forecasts with values for dashboard MAPE KPI."""
    today = datetime.utcnow().date()
    created = 0
    sample_pairs = [
        (rng.choice(store_ids), rng.choice(product_ids))
        for _ in range(min(24, len(store_ids) * len(product_ids)))
    ]

    for store_id, product_id in sample_pairs:
        start = today - timedelta(days=rng.randint(60, 300))
        end = today - timedelta(days=rng.randint(1, 14))
        horizon = min(90, (end - start).days + 30)
        fc = Forecast(
            store_id=store_id,
            product_id=product_id,
            model_type=rng.choice(
                [ForecastModelType.PROPHET, ForecastModelType.ARIMA, ForecastModelType.XGBOOST]
            ),
            horizon_days=horizon,
            start_date=start,
            end_date=end,
            status="completed",
            rmse=round(rng.uniform(8.0, 45.0), 2),
            mae=round(rng.uniform(5.0, 30.0), 2),
            mape=round(rng.uniform(4.5, 18.0), 2),
            created_at=datetime.utcnow() - timedelta(days=rng.randint(1, 20)),
            completed_at=datetime.utcnow(),
        )
        db.add(fc)
        db.flush()

        values = []
        base = rng.uniform(80, 400)
        for d in range(horizon):
            dt = end + timedelta(days=d + 1)
            pred = base * (1 + 0.02 * rng.uniform(-1, 1))
            values.append(
                {
                    "forecast_id": fc.id,
                    "date": dt,
                    "predicted": round(pred, 2),
                    "lower_bound": round(pred * 0.85, 2),
                    "upper_bound": round(pred * 1.15, 2),
                    "actual": round(pred * rng.uniform(0.9, 1.1), 2) if d < 14 else None,
                    "created_at": datetime.utcnow(),
                }
            )
        for i in range(0, len(values), BATCH_SIZE):
            db.bulk_insert_mappings(ForecastValue, values[i : i + BATCH_SIZE])
        created += 1
    db.commit()
    return created


def _seed_anomalies(db, store_ids: Sequence[int], product_ids: Sequence[int], rng: random.Random, count: int) -> int:
    rows = []
    today = datetime.utcnow().date()
    for _ in range(count):
        rows.append(
            Anomaly(
                store_id=rng.choice(store_ids),
                product_id=rng.choice(product_ids) if rng.random() > 0.15 else None,
                anomaly_type=rng.choice(list(AnomalyType)),
                severity=rng.choice(list(AlertSeverity)),
                score=round(rng.uniform(0.55, 0.99), 3),
                description=rng.choice(
                    [
                        "Unusual demand spike detected vs 90-day baseline",
                        "Sales collapse below seasonal lower bound",
                        "Inventory level inconsistent with trailing demand",
                        "Transaction volume outlier on weekend",
                    ]
                ),
                detection_date=today - timedelta(days=rng.randint(0, 45)),
                is_reviewed=rng.random() < 0.35,
                is_false_positive=False,
            )
        )
    db.add_all(rows)
    db.commit()
    return len(rows)


def _seed_recommendations(
    db, store_ids: Sequence[int], product_ids: Sequence[int], rng: random.Random, count: int
) -> int:
    titles = [
        "Increase safety stock before monsoon season",
        "Reduce overstock for slow-moving SKUs",
        "Procure alternators for West region stores",
        "Plan Q4 promotional inventory for Engine category",
    ]
    rows = []
    for i in range(count):
        rows.append(
            Recommendation(
                store_id=rng.choice(store_ids),
                product_id=rng.choice(product_ids) if rng.random() > 0.2 else None,
                rec_type=rng.choice(list(RecommendationType)),
                priority=rng.randint(1, 5),
                title=titles[i % len(titles)],
                description="Generated seed recommendation based on demand and inventory signals.",
                rationale="EWMA trend and stock position indicate actionable adjustment.",
                confidence_score=round(rng.uniform(0.62, 0.95), 2),
                expected_impact="Estimated 8-15% reduction in stockouts over 90 days",
                is_acted=rng.random() < 0.2,
                expires_at=datetime.utcnow() + timedelta(days=rng.randint(14, 90)),
            )
        )
    db.add_all(rows)
    db.commit()
    return len(rows)


def _seed_clusters(db, store_ids: Sequence[int], rng: random.Random) -> int:
    today = datetime.utcnow().date()
    categories = sorted({c for _, _, c, _, _, _ in PRODUCT_SPECS})
    rows = []
    for store_id in store_ids:
        for category in categories:
            rows.append(
                Cluster(
                    store_id=store_id,
                    category=category,
                    sales_ewma=round(rng.uniform(500, 8500), 2),
                    cluster_label=rng.randint(0, 3),
                    cluster_analysis_date=today,
                )
            )
    db.add_all(rows)
    db.commit()
    return len(rows)


def _hash_password(password: str) -> str:
    """Hash password with bcrypt (avoids passlib backend issues on Python 3.14+)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _seed_demo_users(db, password: str) -> int:
    created = 0
    for email, full_name, role in DEMO_USER_SPECS:
        if db.query(User).filter_by(email=email).first():
            continue
        db.add(
            User(
                email=email,
                password_hash=_hash_password(password),
                full_name=full_name,
                role=role,
                is_active=True,
            )
        )
        created += 1
    db.commit()
    return created


def _seed_audit_logs(db, user_ids: Sequence[int], rng: random.Random, count: int) -> int:
    actions = ["login", "forecast_view", "report_export", "inventory_update", "dashboard_view"]
    resources = ["forecast", "inventory", "sales", "report", "user"]
    rows = []
    for _ in range(count):
        rows.append(
            AuditLog(
                user_id=rng.choice(user_ids) if user_ids else None,
                action=rng.choice(actions),
                resource_type=rng.choice(resources),
                resource_id=str(rng.randint(1, 500)),
                details={"source": "seed_bulk_data"},
                ip_address=f"10.0.{rng.randint(1, 5)}.{rng.randint(10, 250)}",
                created_at=datetime.utcnow() - timedelta(days=rng.randint(0, 60)),
            )
        )
    db.add_all(rows)
    db.commit()
    return len(rows)


def _verify_counts(db) -> Dict[str, int]:
    from models import ForecastValue, InventoryAlert

    models = [
        ("stores", Store),
        ("products", Product),
        ("sales", Sale),
        ("inventory_levels", InventoryLevel),
        ("inventory_alerts", InventoryAlert),
        ("forecasts", Forecast),
        ("forecast_values", ForecastValue),
        ("anomalies", Anomaly),
        ("recommendations", Recommendation),
        ("clusters", Cluster),
        ("users", User),
        ("audit_logs", AuditLog),
    ]
    counts = {name: db.query(model).count() for name, model in models}
    return counts


def run_seed(
    sales_count: int = DEFAULT_SALES_COUNT,
    replace: bool = False,
    seed: int = DEFAULT_SEED,
    demo_password: str = "DemoPass123!",
    span_days: int = 700,
) -> Dict[str, int]:
    rng = random.Random(seed)
    end_date = datetime.utcnow().date()

    if not check_db_connection():
        raise RuntimeError("Database connection failed. Check DATABASE_URL in .env")

    _apply_schema()

    with get_db_session() as db:
        if replace:
            logger.info("Replace mode: clearing transactional tables...")
            _clear_transactional_data(db)

        store_map = _ensure_stores(db)
        product_map = _ensure_products(db)
        store_ids = list(store_map.values())
        product_rows = db.query(Product).filter(Product.id.in_(product_map.values())).all()
        product_meta = [(p.id, float(p.selling_price or 25.0)) for p in product_rows]

        existing_sales = db.query(Sale).count()
        to_insert = sales_count if replace else max(0, sales_count - existing_sales)

        if to_insert <= 0:
            logger.info(
                "Sales table already has %s rows (target %s). Skipping sales insert.",
                existing_sales,
                sales_count,
            )
        else:
            logger.info("Generating %s sales records...", to_insert)
            sales_rows = _build_sales_rows(
                rng, store_ids, product_meta, to_insert, end_date, span_days
            )
            inserted = _bulk_insert_sales(db, sales_rows)
            logger.info("Inserted %s sales", inserted)

        inv_created = _bootstrap_inventory(db, rng)
        logger.info("Inventory levels created/updated: %s", inv_created)

        fc_count = _seed_forecasts(db, store_ids, [p[0] for p in product_meta], rng)
        anom_count = _seed_anomalies(db, store_ids, [p[0] for p in product_meta], rng, 80)
        rec_count = _seed_recommendations(db, store_ids, [p[0] for p in product_meta], rng, 60)
        cluster_count = _seed_clusters(db, store_ids, rng)
        user_count = _seed_demo_users(db, demo_password)

        user_ids = [u.id for u in db.query(User).all()]
        audit_count = _seed_audit_logs(db, user_ids, rng, 150)

        counts = _verify_counts(db)
        logger.info("Seed complete. Table counts: %s", counts)
        return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Stocker with realistic bulk demo data")
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_SALES_COUNT,
        help=f"Target number of sales rows (default: {DEFAULT_SALES_COUNT})",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Clear transactional data before seeding (recommended for clean 10k dataset)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="RNG seed for reproducibility")
    parser.add_argument(
        "--demo-password",
        default=os.environ.get("STOCKER_SEED_DEMO_PASSWORD", "DemoPass123!"),
        help="Password for seeded demo users",
    )
    parser.add_argument(
        "--span-days",
        type=int,
        default=700,
        help="Date range width for generated sales (days back from today)",
    )
    args = parser.parse_args()

    try:
        counts = run_seed(
            sales_count=args.count,
            replace=args.replace,
            seed=args.seed,
            demo_password=args.demo_password,
            span_days=args.span_days,
        )
        sales_n = counts.get("sales", 0)
        if sales_n < args.count and not args.replace:
            logger.warning(
                "Sales count %s is below target %s. Re-run with --replace for a clean dataset.",
                sales_n,
                args.count,
            )
        print("\n=== Seed Summary ===")
        for table, n in sorted(counts.items()):
            print(f"  {table}: {n}")
        print("\nDone.")
    except Exception as exc:
        logger.exception("Seed failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
