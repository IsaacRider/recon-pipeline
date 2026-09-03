# Payments Reconciliation Pipeline

An end-to-end data engineering pipeline that reconciles payment records from two
independent sources, the pattern every payments company relies on to verify that
money it *thinks* it collected actually settled.

Two systems record the same payments:

- **Internal transactions** — what our own system says a resident paid.
- **Processor settlements** — what the card processor / bank actually settled.

They never agree perfectly. This pipeline loads both, matches them transaction by
transaction, and flags every discrepancy for review.

## Architecture

```
  CSV sources                DuckDB / Snowflake         dbt models                 Dashboard
 ┌───────────────┐          ┌──────────────────┐      ┌──────────────────┐       ┌──────────────┐
 │ internal_txns │──load──▶ │  raw.raw_internal│─────▶│ stg_internal     │──┐    │  Streamlit   │
 │ processor_set │──load──▶ │  raw.raw_processr│─────▶│ stg_processor    │──┼──▶ │  status +    │
 └───────────────┘          └──────────────────┘      │ recon_results    │◀─┘    │  exceptions  │
        ▲                                              │ recon_summary    │       └──────────────┘
        │                                              └──────────────────┘
   generate_data.py                                     (SQL: FULL OUTER JOIN
                                                          + CASE classification)

        └──────────────── orchestrated by Dagster (generate → load → dbt run → dbt test) ─────────┘
```

Each transaction is classified as:

| Status | Meaning |
|---|---|
| `MATCHED` | In both sources, amounts agree |
| `MISSING_IN_PROCESSOR` | We recorded it; processor never settled it |
| `UNEXPECTED_IN_PROCESSOR` | Processor settled it; we have no record |
| `AMOUNT_MISMATCH` | In both, but amounts disagree |

## Tech stack

- **Python** — data generation, extract/load, and pure reconciliation logic
- **pytest** — unit tests for the matching logic (test-first)
- **DuckDB** — local analytical warehouse (zero setup); swappable for **Snowflake**
- **dbt** — SQL transformation + data modeling (staging → marts) with data tests
- **Dagster** — orchestrates the pipeline as a scheduled dependency graph
- **Streamlit** — reconciliation dashboard (status, dollar exposure, exceptions)
- **GitHub Actions** — CI runs tests + full pipeline on every push

## Quickstart (local, no accounts, no Docker)

```bash
pip install -r requirements.txt

# 1. generate the two mock sources
python scripts/generate_data.py

# 2. extract + load into DuckDB
python scripts/load_to_duckdb.py

# 3. transform + reconcile with dbt
cd recon_dbt
dbt run  --profiles-dir .
dbt test --profiles-dir .
cd ..

# 4. see the results
streamlit run scripts/dashboard.py
```

Or run the whole thing orchestrated:

```bash
dagster dev -f dagster_recon/definitions.py
# open the browser UI, click "Materialize all"
```

## Running against Snowflake instead of DuckDB

The same dbt models run on Snowflake. Set your credentials and switch the target:

```bash
export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=...
python scripts/load_to_snowflake.py
cd recon_dbt && dbt run --profiles-dir . --target snowflake
```

## Project layout

```
scripts/
  generate_data.py       # create two mock payment sources with injected discrepancies
  reconcile.py           # pure-Python reconciliation logic (unit-tested)
  load_to_duckdb.py      # extract + load -> DuckDB (local)
  load_to_snowflake.py   # extract + load -> Snowflake (cloud)
  dashboard.py           # Streamlit BI dashboard
tests/
  test_reconcile.py      # pytest unit tests
recon_dbt/
  models/staging/        # clean + cast each source
  models/marts/          # recon_results (the match) + recon_summary (reporting)
dagster_recon/
  definitions.py         # orchestration DAG + daily schedule
.github/workflows/ci.yml # CI: tests + pipeline on every push
```

## Notes

Reconciliation logic is written twice on purpose: once in Python (`reconcile.py`,
easy to unit-test) and once in SQL (`recon_results.sql`, runs in the warehouse at
scale). They implement the same rules, which is itself a nice cross-check.
