

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

PROJECT_ROOT = "/opt/airflow/project"
CITIES = ["bangkok", "lisbon"]

DEFAULT_ARGS = {
    "owner":            "airbnb_pipeline",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
}

with DAG(
    dag_id="airbnb_market_pipeline",
    default_args=DEFAULT_ARGS,
    description="Airbnb pipeline: ingest → clean → enrich → load star schema",
    schedule_interval="@weekly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["airbnb", "data-engineering"],
) as dag:

    for city in CITIES:

        ingest = BashOperator(
            task_id=f"{city}__ingest",
            bash_command=f"cd {PROJECT_ROOT} && python pipeline/ingestion/ingest_and_profile.py --city {city}",
        )

        clean_listings = BashOperator(
            task_id=f"{city}__clean_listings",
            bash_command=f"cd {PROJECT_ROOT} && python pipeline/cleaning/clean_listings.py --city {city}",
        )

        clean_reviews = BashOperator(
            task_id=f"{city}__clean_reviews",
            bash_command=f"cd {PROJECT_ROOT} && python pipeline/cleaning/clean_reviews.py --city {city}",
        )

        clean_calendar = BashOperator(
            task_id=f"{city}__clean_calendar",
            bash_command=f"cd {PROJECT_ROOT} && python pipeline/cleaning/clean_calendar.py --city {city}",
        )

        clean_neighbourhoods = BashOperator(
            task_id=f"{city}__clean_neighbourhoods",
            bash_command=f"cd {PROJECT_ROOT} && python pipeline/cleaning/clean_neighbourhoods.py --city {city}",
        )

        enrich = BashOperator(
            task_id=f"{city}__enrich",
            bash_command=f"cd {PROJECT_ROOT} && python pipeline/enrichment/enrich_listings.py --city {city}",
        )

        load = BashOperator(
            task_id=f"{city}__load_star_schema",
            bash_command=f"cd {PROJECT_ROOT} && python pipeline/modeling/load_star_schema.py --city {city}",
        )

        # ingest → all cleaning in parallel → enrich → load
        ingest >> [clean_listings, clean_reviews,
                   clean_calendar, clean_neighbourhoods] >> enrich >> load
