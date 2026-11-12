"""Export clean CSV files for the PostgreSQL layer (used by sql/load_data.sql).

Run from the repository root:
    python scripts/export_for_postgres.py

Output folder: data/processed/sql_export/  (ignored by Git, safe to delete)
"""

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MASTER_DATA_PATH, PROCESSED_DATA_DIR  # noqa: E402

OUTPUT_DIR = PROCESSED_DATA_DIR / "sql_export"

# The column order must match the \copy commands in sql/load_data.sql
MASTER_COLUMNS = [
    "Invoice",
    "StockCode",
    "StockCodeNormalized",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "CustomerID",
    "Country",
    "Revenue",
    "IsCancelled",
    "TransactionType",
]

ANOMALY_COLUMNS = [
    "CaseID",
    "Invoice",
    "InvoiceDate",
    "HighestAlertPriority",
    "CasePriority",
    "PrimaryAlertCategory",
    "AlertRevenue",
    "BusinessOwner",
    "RecommendedAction",
    "ReviewStatus",
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    master = pd.read_csv(MASTER_DATA_PATH, low_memory=False)
    master = master[MASTER_COLUMNS].copy()
    master["CustomerID"] = master["CustomerID"].astype("Int64")  # no "12345.0"
    master.to_csv(OUTPUT_DIR / "master.csv", index=False)
    print(f"master.csv: {len(master):,} rows")

    segments = pd.read_csv(PROCESSED_DATA_DIR / "customer_segments.csv.gz")
    segments = segments[["CustomerID", "Cluster"]].astype("int64")
    segments.to_csv(OUTPUT_DIR / "customer_segments.csv", index=False)
    print(f"customer_segments.csv: {len(segments):,} rows")

    cases = pd.read_csv(
        PROCESSED_DATA_DIR / "anomaly_detection" / "anomaly_invoice_cases.csv.gz"
    )
    cases[ANOMALY_COLUMNS].to_csv(
        OUTPUT_DIR / "anomaly_invoice_cases.csv", index=False
    )
    print(f"anomaly_invoice_cases.csv: {len(cases):,} rows")

    print(f"\nDone. Files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
