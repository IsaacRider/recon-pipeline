"""
Dagster orchestration.

This wires the pipeline steps into an ordered dependency graph (a DAG) so the whole
thing runs in sequence and can be scheduled. Each @asset is one step; the function
argument names declare dependencies (dbt models depend on raw data being loaded).

Run the UI:   dagster dev -f dagster_recon/definitions.py
Then click "Materialize all" in the browser, or set a schedule.
"""

import subprocess
from pathlib import Path

from dagster import asset, Definitions, define_asset_job, ScheduleDefinition

ROOT = Path(__file__).resolve().parent.parent
DBT_DIR = ROOT / "recon_dbt"


@asset
def raw_payment_data() -> None:
    """EXTRACT + LOAD: generate mock data and load both sources into DuckDB."""
    subprocess.run(["python", str(ROOT / "scripts" / "generate_data.py")], check=True)
    subprocess.run(["python", str(ROOT / "scripts" / "load_to_duckdb.py")], check=True)


@asset(deps=[raw_payment_data])
def dbt_models() -> None:
    """TRANSFORM: run the dbt staging + reconciliation models."""
    subprocess.run(
        ["dbt", "run", "--profiles-dir", "."], cwd=str(DBT_DIR), check=True
    )


@asset(deps=[dbt_models])
def dbt_tests() -> None:
    """VALIDATE: run dbt data tests on the reconciliation output."""
    subprocess.run(
        ["dbt", "test", "--profiles-dir", "."], cwd=str(DBT_DIR), check=True
    )


recon_job = define_asset_job(name="recon_pipeline")

# run the whole pipeline every day at 2am, the classic nightly-batch pattern
daily_schedule = ScheduleDefinition(job=recon_job, cron_schedule="0 2 * * *")

defs = Definitions(
    assets=[raw_payment_data, dbt_models, dbt_tests],
    jobs=[recon_job],
    schedules=[daily_schedule],
)
