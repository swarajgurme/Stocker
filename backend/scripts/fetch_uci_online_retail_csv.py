#!/usr/bin/env python3
"""
Download the UCI *Online Retail* dataset (real UK e‑commerce transactions) and
emit a CSV in the same shape as ``data.csv`` for ``migrate_csv_to_db``.

Primary source (Excel workbook):
https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx

Dataset page (citation / license):
https://archive.ics.uci.edu/dataset/352/online+retail

The workbook is aggregated to one row per (date, store bucket, product slot),
with ``EWMA`` as a 7‑day exponentially weighted moving average of daily
revenue (quantity × unit price), matching how the bundled sample uses EWMA
as a revenue proxy.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import pandas as pd

UCI_ONLINE_RETAIL_XLSX = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/"
    "Online%20Retail.xlsx"
)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading:\n  {url}\n→ {dest}", file=sys.stderr)
    urllib.request.urlretrieve(url, dest)


def _store_bucket(customer_id: float) -> int:
    """Stable pseudo‑store 0..4 from customer id (no real store id in source)."""
    s = str(int(customer_id))
    h = int(hashlib.md5(s.encode(), usedforsecurity=False).hexdigest(), 16)
    return h % 5


def build_stocker_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Map UCI rows → Stocker migration schema."""
    work = df.copy()
    work = work.rename(
        columns={
            "InvoiceDate": "InvoiceDate",
        }
    )
    if "InvoiceDate" not in work.columns:
        raise ValueError(f"Unexpected columns: {list(work.columns)}")

    work["InvoiceDate"] = pd.to_datetime(work["InvoiceDate"], errors="coerce")
    work = work.dropna(subset=["InvoiceDate", "StockCode"])
    work = work[work["Quantity"] > 0]
    work = work.dropna(subset=["CustomerID"])
    work["CustomerID"] = work["CustomerID"].astype(float)
    work["revenue"] = work["Quantity"].astype(float) * work["UnitPrice"].astype(float)
    work["sale_date"] = work["InvoiceDate"].dt.normalize()

    # UK subset — densest real activity in this file.
    if "Country" in work.columns:
        work = work[work["Country"].astype(str).str.strip() == "United Kingdom"]

    top_codes = (
        work["StockCode"].astype(str).value_counts().head(20).index.tolist()
    )
    code_to_idx = {c: i for i, c in enumerate(top_codes)}
    work = work[work["StockCode"].astype(str).isin(code_to_idx)]
    work["Product Name"] = work["StockCode"].astype(str).map(code_to_idx)

    work["Store ID"] = work["CustomerID"].map(_store_bucket)

    daily = (
        work.groupby(["sale_date", "Store ID", "Product Name"], as_index=False)[
            "revenue"
        ]
        .sum()
        .rename(columns={"sale_date": "Date"})
    )

    daily = daily.sort_values(["Store ID", "Product Name", "Date"])
    daily["EWMA"] = daily.groupby(["Store ID", "Product Name"], group_keys=False)[
        "revenue"
    ].transform(lambda s: s.ewm(span=7, adjust=False).mean())

    daily["Year"] = daily["Date"].dt.year
    daily["Quarter"] = daily["Date"].dt.quarter
    daily["Day"] = daily["Date"].dt.day
    daily["DayOfWeek"] = daily["Date"].dt.weekday
    daily["Category"] = (daily["Product Name"] % 5).astype(int)
    daily["Region"] = daily["Store ID"].astype(int)

    out = daily[
        [
            "Date",
            "Store ID",
            "Product Name",
            "Category",
            "Region",
            "Year",
            "Quarter",
            "Day",
            "DayOfWeek",
            "EWMA",
        ]
    ].copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data_uci_online_retail.csv",
        help="Output CSV path (Stocker format)",
    )
    parser.add_argument(
        "--max-days",
        type=int,
        default=365,
        help="Keep only the last N calendar days after aggregation (default 365)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse existing xlsx next to output (same stem .xlsx)",
    )
    args = parser.parse_args()

    xlsx_path = args.output.with_suffix(".xlsx")
    if not args.skip_download or not xlsx_path.is_file():
        _download(UCI_ONLINE_RETAIL_XLSX, xlsx_path)

    df = pd.read_excel(xlsx_path, engine="openpyxl")
    out = build_stocker_csv(df)
    if args.max_days and not out.empty:
        last = pd.to_datetime(out["Date"]).max()
        cutoff = (last - pd.Timedelta(days=args.max_days)).strftime("%Y-%m-%d")
        out = out[out["Date"] >= cutoff]

    out.to_csv(args.output, index=False)
    print(
        f"Wrote {len(out):,} rows to {args.output} "
        f"(columns: {', '.join(out.columns)})",
        file=sys.stderr,
    )
    print(out.head(8).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
