#!/usr/bin/env python3
"""Export Stocker database dataset summary and samples to a PDF."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import letter, landscape  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from sqlalchemy import func  # noqa: E402

from database import check_db_connection, get_db_session  # noqa: E402
from models import Anomaly, Forecast, InventoryLevel, Product, Sale, Store  # noqa: E402


def _table(data: list[list], col_widths=None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d9488")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdfa")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build_pdf(output_path: Path, sales_sample: int = 80) -> None:
    if not check_db_connection():
        raise RuntimeError("Cannot connect to database. Set DATABASE_URL in .env")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#0f766e"),
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#115e59"),
        spaceBefore=14,
        spaceAfter=8,
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(letter),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story: list = []

    story.append(Paragraph("Stocker Enterprise AI — Dataset Export", title_style))
    story.append(
        Paragraph(
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · "
            "Automotive parts sales, inventory, and forecasting demo data",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    with get_db_session() as db:
        n_stores = db.query(Store).count()
        n_products = db.query(Product).count()
        n_sales = db.query(Sale).count()
        n_inv = db.query(InventoryLevel).count()
        n_fc = db.query(Forecast).count()
        n_anom = db.query(Anomaly).count()

        rev = db.query(func.sum(Sale.revenue)).scalar() or 0
        qty = db.query(func.sum(Sale.quantity)).scalar() or 0
        dmin, dmax = db.query(func.min(Sale.sale_date), func.max(Sale.sale_date)).one()

        summary = [
            ["Table", "Records"],
            ["stores", str(n_stores)],
            ["products", str(n_products)],
            ["sales", str(n_sales)],
            ["inventory_levels", str(n_inv)],
            ["forecasts", str(n_fc)],
            ["anomalies", str(n_anom)],
            ["Total revenue (sales)", f"${float(rev):,.2f}"],
            ["Total units sold", str(int(qty))],
            ["Sale date range", f"{dmin} → {dmax}"],
        ]
        story.append(Paragraph("Dataset overview", h2))
        story.append(_table(summary, col_widths=[3.5 * inch, 4 * inch]))

        # Stores
        story.append(Paragraph("Stores (master data)", h2))
        store_rows = [["Code", "Name", "Region", "City", "Active"]]
        for s in db.query(Store).order_by(Store.store_code).all():
            store_rows.append(
                [
                    s.store_code,
                    (s.name or "")[:40],
                    s.region,
                    (s.city or "")[:20],
                    "Yes" if s.is_active else "No",
                ]
            )
        story.append(_table(store_rows, col_widths=[0.7 * inch, 2.2 * inch, 0.9 * inch, 1.2 * inch, 0.6 * inch]))

        story.append(PageBreak())

        # Products
        story.append(Paragraph("Products (master data)", h2))
        prod_rows = [["Code", "Name", "Category", "Brand", "Price", "SKU"]]
        for p in db.query(Product).order_by(Product.product_code).all():
            prod_rows.append(
                [
                    p.product_code,
                    p.name[:28],
                    p.category[:18],
                    (p.brand or "")[:14],
                    f"${p.selling_price:.2f}" if p.selling_price else "—",
                    (p.sku or "")[:18],
                ]
            )
        story.append(
            _table(
                prod_rows,
                col_widths=[0.65 * inch, 1.8 * inch, 1.3 * inch, 1.1 * inch, 0.75 * inch, 1.4 * inch],
            )
        )

        story.append(Spacer(1, 0.15 * inch))

        # Sales by category
        story.append(Paragraph("Sales by category (aggregated)", h2))
        cat_rows = [["Category", "Revenue", "Units", "Transactions"]]
        cat_q = (
            db.query(
                Product.category,
                func.sum(Sale.revenue),
                func.sum(Sale.quantity),
                func.count(Sale.id),
            )
            .join(Product, Sale.product_id == Product.id)
            .group_by(Product.category)
            .order_by(func.sum(Sale.revenue).desc())
            .all()
        )
        for cat, rev_c, units, txs in cat_q:
            cat_rows.append(
                [
                    cat,
                    f"${float(rev_c or 0):,.2f}",
                    str(int(units or 0)),
                    str(int(txs or 0)),
                ]
            )
        story.append(_table(cat_rows, col_widths=[2 * inch, 1.5 * inch, 1 * inch, 1.2 * inch]))

        story.append(PageBreak())

        # Sales sample
        story.append(
            Paragraph(
                f"Sales transactions (sample: latest {sales_sample} rows)",
                h2,
            )
        )
        sales_rows = [
            [
                "Date",
                "Store",
                "Product",
                "Category",
                "Qty",
                "Revenue",
                "EWMA",
            ]
        ]
        sample_q = (
            db.query(Sale, Store.store_code, Product.name, Product.category)
            .join(Store, Sale.store_id == Store.id)
            .join(Product, Sale.product_id == Product.id)
            .order_by(Sale.sale_date.desc(), Sale.id.desc())
            .limit(sales_sample)
            .all()
        )
        for sale, code, pname, cat in sample_q:
            sales_rows.append(
                [
                    str(sale.sale_date),
                    code,
                    pname[:22],
                    cat[:16],
                    str(sale.quantity),
                    f"{sale.revenue:.2f}",
                    f"{sale.ewma:.2f}",
                ]
            )
        story.append(
            _table(
                sales_rows,
                col_widths=[
                    0.95 * inch,
                    0.55 * inch,
                    1.5 * inch,
                    1.1 * inch,
                    0.45 * inch,
                    0.75 * inch,
                    0.65 * inch,
                ],
            )
        )

        story.append(Spacer(1, 0.15 * inch))
        story.append(
            Paragraph(
                f"<i>Full dataset: {n_sales:,} sales rows in PostgreSQL "
                f"(stocker_db). CSV sources: backend/data.csv, "
                f"backend/data_uci_online_retail.csv</i>",
                styles["Normal"],
            )
        )

    doc.build(story)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Stocker dataset to PDF")
    parser.add_argument(
        "-o",
        "--output",
        default=str(backend_dir / "exports" / "stocker_dataset.pdf"),
        help="Output PDF path",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=80,
        help="Number of sales rows to include in sample table",
    )
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(out, sales_sample=args.sample)
    print(f"PDF written to: {out.resolve()}")


if __name__ == "__main__":
    main()
