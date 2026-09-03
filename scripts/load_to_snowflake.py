"""
EXTRACT + LOAD step (the E and L of ELT).

Reads the two raw CSVs and loads them into Snowflake as raw tables. dbt then does
the TRANSFORM step on top (staging + reconciliation marts).

Credentials come from environment variables so nothing secret lives in the repo:

  export SNOWFLAKE_ACCOUNT=xxxxx-xxxxx
  export SNOWFLAKE_USER=your_user
  export SNOWFLAKE_PASSWORD=your_password
  export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
  export SNOWFLAKE_DATABASE=RECON
  export SNOWFLAKE_SCHEMA=RAW

Run:  python scripts/load_to_snowflake.py

(If you have not set up Snowflake yet, use load_to_duckdb.py instead for a
zero-signup local run. Same models work on both.)
"""

import os
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def get_connection():
    import snowflake.connector

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "RECON"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "RAW"),
    )


def load_table(conn, df: pd.DataFrame, table: str):
    from snowflake.connector.pandas_tools import write_pandas

    # uppercase columns; Snowflake is case-sensitive-ish and defaults to upper
    df.columns = [c.upper() for c in df.columns]
    cur = conn.cursor()
    cols = ", ".join(f"{c} STRING" for c in df.columns)
    cur.execute(f"CREATE OR REPLACE TABLE {table} ({cols})")
    write_pandas(conn, df, table.upper(), auto_create_table=False)
    print(f"loaded {len(df):>4} rows -> {table}")


def main():
    conn = get_connection()
    internal = pd.read_csv(DATA_DIR / "internal_transactions.csv")
    processor = pd.read_csv(DATA_DIR / "processor_settlements.csv")
    load_table(conn, internal, "RAW_INTERNAL_TRANSACTIONS")
    load_table(conn, processor, "RAW_PROCESSOR_SETTLEMENTS")
    conn.close()
    print("done.")


if __name__ == "__main__":
    main()
