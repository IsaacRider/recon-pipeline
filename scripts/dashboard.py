"""
Reconciliation dashboard (BI / data visualization layer).

Reads the dbt-built marts and shows: status breakdown, dollar exposure, and a
browsable table of flagged exceptions, the view an ops team would use to chase
down unmatched payments.

Run:  streamlit run scripts/dashboard.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "recon.duckdb"

st.set_page_config(page_title="Payments Reconciliation", layout="wide")
st.title("Payments Reconciliation Dashboard")
st.caption("Internal transactions vs processor settlements")


@st.cache_data
def load(query: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(query).fetchdf()
    con.close()
    return df


results = load("SELECT * FROM main.recon_results")
summary = load("SELECT * FROM main.recon_summary")

# --- top-line metrics ---
total = len(results)
matched = (results["recon_status"] == "MATCHED").sum()
flagged = total - matched
match_rate = matched / total * 100 if total else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total transactions", f"{total:,}")
c2.metric("Matched", f"{matched:,}")
c3.metric("Flagged for review", f"{flagged:,}")
c4.metric("Match rate", f"{match_rate:.1f}%")

# --- status breakdown chart ---
st.subheader("Status breakdown")
status_counts = results["recon_status"].value_counts()
st.bar_chart(status_counts)

# --- dollar exposure by agency ---
st.subheader("Flagged dollar difference by agency")
exposure = (
    results[results["recon_status"] != "MATCHED"]
    .assign(agency=lambda d: d["agency"].fillna("UNKNOWN"))
    .groupby("agency")["amount_difference"]
    .sum()
    .abs()
)
st.bar_chart(exposure)

# --- exceptions table ---
st.subheader("Exceptions (everything not MATCHED)")
status_filter = st.multiselect(
    "Filter by status",
    options=sorted(results["recon_status"].unique()),
    default=["MISSING_IN_PROCESSOR", "UNEXPECTED_IN_PROCESSOR", "AMOUNT_MISMATCH"],
)
st.dataframe(
    results[results["recon_status"].isin(status_filter)].reset_index(drop=True),
    use_container_width=True,
)
