"""
Zero-signup local alternative to Snowflake.

DuckDB is an in-process analytical database (think "SQLite for analytics"). It needs
no server, no Docker, no account, just `pip install duckdb`. The SAME dbt models run
on it, so you can build and demo the whole pipeline offline, then point at Snowflake
later by swapping the dbt profile.

Run:  python scripts/load_to_duckdb.py
Produces:  recon.duckdb  with two raw tables.
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = ROOT / "recon.duckdb"


def main():
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.raw_internal_transactions AS
        SELECT * FROM read_csv_auto('{DATA_DIR / "internal_transactions.csv"}')
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.raw_processor_settlements AS
        SELECT * FROM read_csv_auto('{DATA_DIR / "processor_settlements.csv"}')
        """
    )

    for t in ["raw.raw_internal_transactions", "raw.raw_processor_settlements"]:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"loaded {n:>4} rows -> {t}")

    con.close()
    print(f"done. database at {DB_PATH}")


if __name__ == "__main__":
    main()
