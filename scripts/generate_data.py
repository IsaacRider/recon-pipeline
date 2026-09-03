"""
Generate two mock payment datasets that represent the SAME payments seen from
two different systems, the way a real payments company sees them:

  1. internal_transactions.csv  - what PayIt's own system recorded (source of truth A)
  2. processor_settlements.csv   - what the card processor / bank settled (source of truth B)

We deliberately inject realistic discrepancies so the reconciliation model has
something to catch:
  - MATCHED:      appears in both, same amount           (the happy path)
  - MISSING:      in internal, never settled by processor (money we think we got but didn't)
  - UNEXPECTED:   settled by processor, no internal record (money we weren't expecting)
  - AMOUNT_MISMATCH: in both, but the amounts disagree     (partial capture, fees, bug)

Run:  python scripts/generate_data.py
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # deterministic so tests are reproducible

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

AGENCIES = ["KS_DMV", "KS_PARKS", "NC_DMV", "COURT_FINES", "PROPERTY_TAX"]
N = 500  # number of "true" payments


def a_transaction(i: int):
    txn_id = f"TXN{i:06d}"
    amount = round(random.uniform(15, 450), 2)
    agency = random.choice(AGENCIES)
    ts = datetime(2026, 8, 1) + timedelta(minutes=random.randint(0, 43200))
    return {
        "transaction_id": txn_id,
        "agency": agency,
        "amount": amount,
        "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():
    truth = [a_transaction(i) for i in range(1, N + 1)]

    internal_rows = []
    processor_rows = []

    for row in truth:
        r = random.random()
        if r < 0.85:
            # MATCHED: in both, same amount
            internal_rows.append(row)
            processor_rows.append(_to_settlement(row))
        elif r < 0.92:
            # MISSING: internal recorded it, processor never settled it
            internal_rows.append(row)
        elif r < 0.97:
            # AMOUNT_MISMATCH: both have it, processor amount differs
            internal_rows.append(row)
            bad = dict(row)
            bad["amount"] = round(row["amount"] - random.uniform(1, 20), 2)
            processor_rows.append(_to_settlement(bad))
        else:
            # UNEXPECTED: processor settled something internal never recorded
            processor_rows.append(_to_settlement(row))

    _write_csv(
        DATA_DIR / "internal_transactions.csv",
        ["transaction_id", "agency", "amount", "created_at"],
        internal_rows,
    )
    _write_csv(
        DATA_DIR / "processor_settlements.csv",
        ["settlement_id", "transaction_id", "settled_amount", "settled_at"],
        processor_rows,
    )

    print(f"internal_transactions.csv : {len(internal_rows)} rows")
    print(f"processor_settlements.csv : {len(processor_rows)} rows")


def _to_settlement(row: dict):
    return {
        "settlement_id": "SET" + row["transaction_id"][3:],
        "transaction_id": row["transaction_id"],
        "settled_amount": row["amount"],
        "settled_at": row["created_at"],
    }


def _write_csv(path: Path, fieldnames, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
