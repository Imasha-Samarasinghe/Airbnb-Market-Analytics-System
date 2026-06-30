import sys
from datetime import datetime
from dotenv import load_dotenv
import argparse
import os
from sqlalchemy import create_engine, text
import numpy as np
import pandas as pd

# =============================================================================
# Airbnb Market Analytics System
# Milestone 4: Star Schema — Design & Load into PostgreSQL
# Usage: python pipeline/modeling/load_star_schema.py --city bangkok
#        python pipeline/modeling/load_star_schema.py --city lisbon
# =============================================================================


load_dotenv()

# =============================================================================
# CONNECTION
# =============================================================================


def get_engine():
    host = os.getenv("DB_HOST",     "localhost")
    port = os.getenv("DB_PORT",     "5432")
    name = os.getenv("DB_NAME",     "airbnb_analytics")
    user = os.getenv("DB_USER",     "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url)


def check_db_connection(engine):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"\n{'!'*60}")
        print(f"  DATABASE CONNECTION FAILED")
        print(f"{'!'*60}")
        print(f"  Error: {e}")
        print(f"\n  Start PostgreSQL with:  docker compose up -d")
        print(f"  Then re-run this script.")
        print(f"  Your cleaned CSVs in data/processed/ are intact.")
        print(f"{'!'*60}\n")
        return False


def get_config(city):
    return {
        "city":               city,
        "enriched_file":      f"data/processed/{city}/listings_enriched.csv",
        "reviews_file":       f"data/processed/{city}/reviews_clean.csv",
        "calendar_file":      f"data/processed/{city}/calendar_clean.csv",
        "neighbourhoods_file": f"data/processed/{city}/neighbourhoods_clean.csv",
    }


# =============================================================================
# SCHEMA — single source of truth for all cities
# neighbourhood_group is nullable so Bangkok (no group) and Lisbon (has group)
# both work without schema changes.
# =============================================================================

def create_schema(engine):
    print("\nCreating schema (if not exists)...")
    with engine.connect() as conn:
        conn.execute(text("""

            CREATE TABLE IF NOT EXISTS dim_host (
                host_id                    BIGINT,
                city                       VARCHAR(50),
                host_name                  TEXT,
                host_since                 DATE,
                host_location              TEXT,
                host_response_time         TEXT,
                host_response_rate         FLOAT,
                host_acceptance_rate       FLOAT,
                host_is_superhost          BOOLEAN,
                host_has_profile_pic       BOOLEAN,
                host_identity_verified     BOOLEAN,
                host_listings_count        FLOAT,
                host_total_listings_count  FLOAT,
                host_tenure_years          FLOAT,
                is_commercial_host         BOOLEAN,
                PRIMARY KEY (host_id, city)
            );

            CREATE TABLE IF NOT EXISTS dim_neighbourhood (
                neighbourhood_id    INT,
                city                VARCHAR(50),
                neighbourhood       TEXT,
                neighbourhood_group TEXT,          -- nullable: Bangkok has none, Lisbon has municipality groups
                geometry_type       TEXT,
                listing_count       INT,
                median_price        FLOAT,
                avg_rating          FLOAT,
                avg_occupancy       FLOAT,
                PRIMARY KEY (neighbourhood_id, city)
            );

            CREATE TABLE IF NOT EXISTS dim_room_type (
                room_type_id   SERIAL,
                city           VARCHAR(50),
                room_type      TEXT,
                listing_count  INT,
                avg_price      FLOAT,
                avg_occupancy  FLOAT,
                PRIMARY KEY (room_type_id, city)
            );

            CREATE TABLE IF NOT EXISTS dim_property_type (
                property_type_id  SERIAL,
                city              VARCHAR(50),
                property_type     TEXT,
                listing_count     INT,
                avg_price         FLOAT,
                PRIMARY KEY (property_type_id, city)
            );

            CREATE TABLE IF NOT EXISTS dim_date (
                date_id      INT,
                city         VARCHAR(50),
                date         DATE,
                year         INT,
                month        INT,
                month_name   TEXT,
                quarter      INT,
                day_of_week  TEXT,
                is_weekend   BOOLEAN,
                PRIMARY KEY (date_id, city)
            );

            CREATE TABLE IF NOT EXISTS fact_listings (
                listing_id                      BIGINT,
                city                            VARCHAR(50),
                host_id                         BIGINT,
                neighbourhood_cleansed          TEXT,
                room_type                       TEXT,
                property_type                   TEXT,
                property_type_grouped           TEXT,
                price                           FLOAT,
                price_per_bedroom               FLOAT,
                price_vs_neighbourhood          FLOAT,
                price_tier                      TEXT,
                minimum_nights                  FLOAT,
                maximum_nights                  FLOAT,
                availability_30                 INT,
                availability_60                 INT,
                availability_90                 INT,
                availability_365                INT,
                number_of_reviews               INT,
                number_of_reviews_ltm           INT,
                number_of_reviews_l30d          INT,
                reviews_per_month               FLOAT,
                review_scores_rating            FLOAT,
                review_scores_accuracy          FLOAT,
                review_scores_cleanliness       FLOAT,
                review_scores_checkin           FLOAT,
                review_scores_communication     FLOAT,
                review_scores_location          FLOAT,
                review_scores_value             FLOAT,
                review_score_composite          FLOAT,
                review_velocity                 FLOAT,
                occupancy_rate                  FLOAT,
                booked_days                     INT,
                available_days                  INT,
                total_days                      INT,
                estimated_annual_revenue        FLOAT,
                host_tenure_years               FLOAT,
                instant_bookable                BOOLEAN,
                has_availability                BOOLEAN,
                calculated_host_listings_count  INT,
                last_scraped                    DATE,
                PRIMARY KEY (listing_id, city)
            );

            CREATE TABLE IF NOT EXISTS fact_reviews (
                review_id         BIGINT,
                city              VARCHAR(50),
                listing_id        BIGINT,
                reviewer_id       BIGINT,
                reviewer_name     TEXT,
                date              DATE,
                comment_length    INT,
                review_year       INT,
                review_month      INT,
                review_year_month TEXT,
                PRIMARY KEY (review_id, city)
            );

            CREATE TABLE IF NOT EXISTS fact_calendar (
                listing_id      BIGINT,
                city            VARCHAR(50),
                date            DATE,
                available       BOOLEAN,
                minimum_nights  INT,
                maximum_nights  INT,
                day_of_week     TEXT,
                month           INT,
                year            INT,
                year_month      TEXT,
                is_weekend      BOOLEAN
            );

            CREATE TABLE IF NOT EXISTS pipeline_metadata (
                run_id         SERIAL PRIMARY KEY,
                city           VARCHAR(50),
                run_timestamp  TIMESTAMP,
                tables_loaded  INT,
                total_rows     BIGINT,
                status         VARCHAR(20)
            );

        """))
        conn.commit()
    print("Schema ready.")


def migrate_schema(engine):
    """
    Add any columns that may be missing from tables created by older pipeline runs.
    Safe to run repeatedly — uses IF NOT EXISTS / exception handling.
    """
    print("\nChecking for schema migrations...")
    migrations = [
        # Add neighbourhood_group if missing (created before Lisbon was added)
        "ALTER TABLE dim_neighbourhood ADD COLUMN IF NOT EXISTS neighbourhood_group TEXT;",
        # Add property_type_grouped if missing
        "ALTER TABLE fact_listings ADD COLUMN IF NOT EXISTS property_type_grouped TEXT;",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                print(f"  Migration applied: {sql[:60]}...")
            except Exception:
                pass  # Column already exists or not supported
        conn.commit()
    print("Schema migrations complete.")


def drop_city_data(engine, city):
    print(f"\nClearing existing data for city: {city}...")
    tables = [
        "fact_calendar", "fact_reviews", "fact_listings",
        "dim_date", "dim_property_type", "dim_room_type",
        "dim_neighbourhood", "dim_host"
    ]
    with engine.connect() as conn:
        for table in tables:
            try:
                conn.execute(
                    text(f"DELETE FROM {table} WHERE city = :city"),
                    {"city": city}
                )
            except Exception:
                pass
        conn.commit()
    print("Existing city data cleared.")


# =============================================================================
# DIMENSION BUILDERS
# =============================================================================

def build_dim_host(listings):
    print("  Building dim_host...")
    host_cols = [
        "host_id", "host_name", "host_since", "host_location",
        "host_response_time", "host_response_rate", "host_acceptance_rate",
        "host_is_superhost", "host_has_profile_pic", "host_identity_verified",
        "host_listings_count", "host_total_listings_count",
        "host_tenure_years", "is_commercial_host"
    ]
    available = [c for c in host_cols if c in listings.columns]
    dim = listings[available].drop_duplicates(
        subset=["host_id"]).reset_index(drop=True)
    print(f"    → {len(dim):,} unique hosts")
    return dim


def build_dim_neighbourhood(listings, neighbourhoods_df):
    print("  Building dim_neighbourhood...")
    dim = neighbourhoods_df.copy()

    stats = listings.groupby("neighbourhood_cleansed").agg(
        listing_count=("id",                   "count"),
        median_price=("price",                "median"),
        avg_rating=("review_scores_rating", "mean"),
        avg_occupancy=("occupancy_rate",        "mean"),
    ).round(2).reset_index()

    dim = dim.merge(
        stats,
        left_on="neighbourhood",
        right_on="neighbourhood_cleansed",
        how="left"
    ).drop(columns=["neighbourhood_cleansed"], errors="ignore")

    # Ensure neighbourhood_group column always exists (may be absent for Bangkok)
    if "neighbourhood_group" not in dim.columns:
        dim["neighbourhood_group"] = None

    print(f"    → {len(dim):,} neighbourhoods")
    return dim


def build_dim_room_type(listings):
    print("  Building dim_room_type...")
    stats = listings.groupby("room_type").agg(
        listing_count=("id",             "count"),
        avg_price=("price",          "mean"),
        avg_occupancy=("occupancy_rate", "mean"),
    ).round(2).reset_index()
    stats.insert(0, "room_type_id", range(1, len(stats) + 1))
    print(f"    → {len(stats):,} room types: {stats['room_type'].tolist()}")
    return stats


def build_dim_property_type(listings):
    print("  Building dim_property_type...")
    stats = listings.groupby("property_type").agg(
        listing_count=("id",    "count"),
        avg_price=("price", "mean"),
    ).round(2).reset_index()
    stats.insert(0, "property_type_id", range(1, len(stats) + 1))
    print(f"    → {len(stats):,} property types")
    return stats


def build_dim_date(reviews, calendar):
    print("  Building dim_date...")
    review_dates = reviews["date"].dropna()
    calendar_dates = calendar["date"].dropna()
    all_dates = pd.concat([review_dates, calendar_dates]
                          ).dt.normalize().unique()
    dim = pd.DataFrame({"date": pd.to_datetime(sorted(all_dates))})
    dim["year"] = dim["date"].dt.year
    dim["month"] = dim["date"].dt.month
    dim["month_name"] = dim["date"].dt.month_name()
    dim["quarter"] = dim["date"].dt.quarter
    dim["day_of_week"] = dim["date"].dt.day_name()
    dim["is_weekend"] = dim["day_of_week"].isin(["Saturday", "Sunday"])
    dim.insert(0, "date_id", range(1, len(dim) + 1))
    print(f"    → {len(dim):,} unique dates")
    return dim


# =============================================================================
# FACT BUILDERS
# =============================================================================

def build_fact_listings(listings):
    print("  Building fact_listings...")
    desired = [
        "id", "host_id", "neighbourhood_cleansed",
        "room_type", "property_type", "property_type_grouped",
        "price", "price_per_bedroom", "price_vs_neighbourhood", "price_tier",
        "minimum_nights", "maximum_nights",
        "availability_30", "availability_60", "availability_90", "availability_365",
        "number_of_reviews", "number_of_reviews_ltm", "number_of_reviews_l30d",
        "reviews_per_month",
        "review_scores_rating", "review_scores_accuracy", "review_scores_cleanliness",
        "review_scores_checkin", "review_scores_communication",
        "review_scores_location", "review_scores_value",
        "review_score_composite", "review_velocity",
        "occupancy_rate", "booked_days", "available_days", "total_days",
        "estimated_annual_revenue", "host_tenure_years",
        "instant_bookable", "has_availability",
        "calculated_host_listings_count", "last_scraped",
    ]
    available = [c for c in desired if c in listings.columns]
    fact = listings[available].copy().rename(columns={"id": "listing_id"})
    print(f"    → {len(fact):,} listings")
    return fact


def build_fact_reviews(reviews):
    print("  Building fact_reviews...")
    fact = reviews[[
        "id", "listing_id", "reviewer_id", "reviewer_name",
        "date", "comment_length", "review_year", "review_month", "review_year_month"
    ]].copy().rename(columns={"id": "review_id"})
    print(f"    → {len(fact):,} reviews")
    return fact


def build_fact_calendar(calendar):
    print("  Building fact_calendar...")
    fact = calendar[[
        "listing_id", "date", "available", "minimum_nights", "maximum_nights",
        "day_of_week", "month", "year", "year_month", "is_weekend"
    ]].copy()
    print(f"    → {len(fact):,} calendar rows")
    return fact


# =============================================================================
# LOAD
# =============================================================================

def load_table(df, table_name, engine, city, chunksize=10000):
    df = df.copy()
    df["city"] = city
    df.to_sql(table_name, engine, if_exists="append", index=False,
              chunksize=chunksize, method="multi")
    print(f"  ✓ {table_name}: {len(df):,} rows loaded")


# =============================================================================
# ANALYTICAL QUERIES
# =============================================================================

def run_analytical_queries(engine, city):
    print(f"\n{'='*60}")
    print(f"ANALYTICAL SQL QUERIES — {city.upper()}")
    print("=" * 60)

    queries = {
        "Top 5 neighbourhoods by average price": f"""
            SELECT neighbourhood_cleansed,
                   ROUND(AVG(price)::numeric, 0) AS avg_price,
                   COUNT(*) AS listing_count
            FROM fact_listings
            WHERE price IS NOT NULL AND city = '{city}'
            GROUP BY neighbourhood_cleansed
            ORDER BY avg_price DESC LIMIT 5;
        """,
        "Superhost vs Non-Superhost": f"""
            SELECT h.host_is_superhost,
                   COUNT(*) AS listing_count,
                   ROUND(AVG(f.price)::numeric, 0) AS avg_price,
                   ROUND(AVG(f.review_scores_rating)::numeric, 3) AS avg_rating,
                   ROUND(AVG(f.occupancy_rate)::numeric, 1) AS avg_occupancy
            FROM fact_listings f
            JOIN dim_host h ON f.host_id = h.host_id AND f.city = h.city
            WHERE h.host_is_superhost IS NOT NULL AND f.city = '{city}'
            GROUP BY h.host_is_superhost ORDER BY h.host_is_superhost DESC;
        """,
        "Room type breakdown": f"""
            SELECT room_type, COUNT(*) AS listing_count,
                   ROUND(AVG(price)::numeric, 0) AS avg_price,
                   ROUND(AVG(occupancy_rate)::numeric, 1) AS avg_occupancy
            FROM fact_listings WHERE city = '{city}'
            GROUP BY room_type ORDER BY listing_count DESC;
        """,
        "Review volume by year": f"""
            SELECT review_year, COUNT(*) AS review_count
            FROM fact_reviews WHERE city = '{city}'
            GROUP BY review_year ORDER BY review_year;
        """,
        "Price tier distribution": f"""
            SELECT price_tier, COUNT(*) AS listing_count,
                   ROUND(AVG(occupancy_rate)::numeric, 1) AS avg_occupancy,
                   ROUND(AVG(price)::numeric, 0) AS avg_price
            FROM fact_listings
            WHERE price_tier IS NOT NULL AND city = '{city}'
            GROUP BY price_tier ORDER BY avg_price;
        """,
    }

    with engine.connect() as conn:
        for title, query in queries.items():
            print(f"\n{title}:")
            print("-" * 40)
            try:
                result = pd.read_sql(text(query), conn)
                print(result.to_string(index=False))
            except Exception as e:
                print(f"  Query error: {e}")


# =============================================================================
# METADATA
# =============================================================================

def log_pipeline_run(engine, city, tables_loaded, rows_loaded):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO pipeline_metadata (city, run_timestamp, tables_loaded, total_rows, status)
            VALUES (:city, :ts, :tables, :rows, :status)
        """), {"city": city, "ts": datetime.now(),
               "tables": tables_loaded, "rows": rows_loaded, "status": "SUCCESS"})
        conn.commit()
    print(f"\nRun logged to pipeline_metadata.")


# =============================================================================
# MAIN
# =============================================================================

def main(city):
    config = get_config(city)

    print("=" * 60)
    print("MILESTONE 4: STAR SCHEMA LOAD")
    print(f"City: {city.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\nLoading processed files...")
    listings = pd.read_csv(
        config["enriched_file"],
        parse_dates=["last_scraped", "host_since", "first_review",
                     "last_review", "calendar_last_scraped"],
        low_memory=False
    )
    reviews = pd.read_csv(config["reviews_file"],       parse_dates=["date"])
    calendar = pd.read_csv(config["calendar_file"],      parse_dates=["date"])
    neighbourhoods = pd.read_csv(config["neighbourhoods_file"])

    print(f"  listings:       {len(listings):,} rows")
    print(f"  reviews:        {len(reviews):,} rows")
    print(f"  calendar:       {len(calendar):,} rows")
    print(f"  neighbourhoods: {len(neighbourhoods):,} rows")

    print("\nBuilding tables in memory...")
    dim_host = build_dim_host(listings)
    dim_neighbourhood = build_dim_neighbourhood(listings, neighbourhoods)
    dim_room_type = build_dim_room_type(listings)
    dim_property_type = build_dim_property_type(listings)
    dim_date = build_dim_date(reviews, calendar)
    fact_listings_df = build_fact_listings(listings)
    fact_reviews_df = build_fact_reviews(reviews)
    fact_calendar_df = build_fact_calendar(calendar)

    print("\nConnecting to PostgreSQL...")
    engine = get_engine()
    if not check_db_connection(engine):
        print("Skipping DB load. CSVs are saved in data/processed/.")
        sys.exit(0)
    print("Connected.")

    create_schema(engine)
    migrate_schema(engine)   # ← adds missing columns to tables from older runs
    drop_city_data(engine, city)

    print("\nLoading into PostgreSQL...")
    load_table(dim_host,          "dim_host",          engine, city)
    load_table(dim_neighbourhood, "dim_neighbourhood", engine, city)
    load_table(dim_room_type,     "dim_room_type",     engine, city)
    load_table(dim_property_type, "dim_property_type", engine, city)
    load_table(dim_date,          "dim_date",          engine, city)
    load_table(fact_listings_df,  "fact_listings",     engine, city)
    load_table(fact_reviews_df,   "fact_reviews",      engine, city)

    print("\n  Loading fact_calendar (large — may take a few minutes)...")
    load_table(fact_calendar_df, "fact_calendar",
               engine, city, chunksize=50000)

    total_rows = sum([
        len(dim_host), len(dim_neighbourhood), len(dim_room_type),
        len(dim_property_type), len(dim_date),
        len(fact_listings_df), len(fact_reviews_df), len(fact_calendar_df)
    ])

    log_pipeline_run(engine, city, tables_loaded=8, rows_loaded=total_rows)
    run_analytical_queries(engine, city)

    print(f"\n{'='*60}")
    print(f"COMPLETE — {city.upper()} | {total_rows:,} total rows loaded")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", type=str, default="bangkok")
    args = parser.parse_args()
    main(args.city)
