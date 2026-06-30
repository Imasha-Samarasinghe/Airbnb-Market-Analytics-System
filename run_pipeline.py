# =============================================================================
# Airbnb Market Analytics System
# Master Pipeline Runner — ingestion + cleaning + enrichment for any city
# Usage:
#   Single city:    python pipeline/run_pipeline.py --city bangkok
#   Multiple cities: python pipeline/run_pipeline.py --city bangkok lisbon
#   All cities:     python pipeline/run_pipeline.py --city all
# =============================================================================

import argparse
import subprocess
import sys
from datetime import datetime

# All cities the pipeline knows about.
# Add new cities here as you expand the project.
ALL_CITIES = ["bangkok", "lisbon"]

SCRIPTS = [
    "pipeline/ingestion/ingest_and_profile.py",
    "pipeline/cleaning/clean_listings.py",
    "pipeline/cleaning/clean_reviews.py",
    "pipeline/cleaning/clean_calendar.py",
    "pipeline/cleaning/clean_neighbourhoods.py",
    "pipeline/enrichment/enrich_listings.py",
    "pipeline/modeling/load_star_schema.py",
]


def run_script(script_path, city):
    print(f"\n{'='*60}")
    print(f"Running: {script_path} --city {city}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, script_path, "--city", city],
        capture_output=False
    )

    if result.returncode != 0:
        print(
            f"\n ERROR in {script_path} for city '{city}'. Stopping pipeline.")
        sys.exit(1)

    print(f"✓ {script_path} completed successfully.")


def run_city(city):
    print(f"\n{'#'*60}")
    print(f"# STARTING FULL PIPELINE FOR: {city.upper()}")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    for script in SCRIPTS:
        run_script(script, city)

    print(f"\n{'#'*60}")
    print(f"# PIPELINE COMPLETE FOR: {city.upper()}")
    print(f"# Output: data/processed/{city}/")
    print(f"# Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")


def main(cities):
    start_time = datetime.now()

    print("=" * 60)
    print("AIRBNB MARKET ANALYTICS — MASTER PIPELINE")
    print(f"Cities: {', '.join(c.upper() for c in cities)}")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    for city in cities:
        run_city(city)

    elapsed = (datetime.now() - start_time).seconds
    print(f"\n{'='*60}")
    print(f"ALL CITIES COMPLETE: {', '.join(c.upper() for c in cities)}")
    print(f"Total time: {elapsed // 60}m {elapsed % 60}s")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the full Airbnb analytics pipeline for one or more cities."
    )
    parser.add_argument(
        "--city", nargs="+", default=["bangkok"],
        help=(
            "City name(s) to process. Examples:\n"
            "  --city bangkok\n"
            "  --city bangkok lisbon\n"
            "  --city all  (runs all configured cities)"
        )
    )
    args = parser.parse_args()

    # Handle 'all' keyword
    cities = ALL_CITIES if args.city == ["all"] else args.city

    # Validate city names
    unknown = [c for c in cities if c not in ALL_CITIES]
    if unknown:
        print(f"ERROR: Unknown city/cities: {unknown}")
        print(f"Known cities: {ALL_CITIES}")
        print(f"To add a new city, update ALL_CITIES in this file and add")
        print(f"its config to CITY_CONFIG in clean_listings.py and enrich_listings.py")
        sys.exit(1)

    main(cities)
