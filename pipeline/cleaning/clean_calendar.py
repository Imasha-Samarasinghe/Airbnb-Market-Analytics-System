# =============================================================================
# Airbnb Market Analytics System
# Milestone 3: Data Cleaning — Calendar
# City: Configurable
# =============================================================================

import pandas as pd
import os
import argparse
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================


def get_config(city):
    return {
        "city": city,
        "input_file": f"data/raw/{city}/calendar.csv",
        "output_file": f"data/processed/{city}/calendar_clean.csv",
    }

# =============================================================================
# CLEANING FUNCTIONS
# =============================================================================


def load_data(path):
    print(f"Loading {path}...")
    # Parse date directly on load to save memory
    df = pd.read_csv(
        path,
        low_memory=False,
        parse_dates=["date"],
    )
    print(f"Loaded: {df.shape[0]:,} rows x {df.shape[1]} columns")
    return df


def clean_availability(df):
    print(f"\n--- Converting availability column ---")
    df["available"] = df["available"].map({"t": True, "f": False})
    available_count = df["available"].sum()
    total = len(df)
    pct = available_count / total * 100
    print(f"Available days: {available_count:,} ({pct:.1f}%)")
    print(
        f"Booked/unavailable days: {total - available_count:,} ({100 - pct:.1f}%)")
    return df


def drop_empty_columns(df):
    print(f"\n--- Dropping 100% null columns ---")
    before = df.shape[1]
    null_cols = [c for c in df.columns if df[c].isnull().all()]
    print(f"Dropping: {null_cols}")
    df = df.drop(columns=null_cols)
    after = df.shape[1]
    print(f"Columns before: {before} → after: {after}")
    return df


def derive_features(df):
    print(f"\n--- Deriving calculated fields ---")

    df["day_of_week"] = df["date"].dt.day_name()
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    df["is_weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"])

    weekend_avail = df[df["is_weekend"]]["available"].mean() * 100
    weekday_avail = df[~df["is_weekend"]]["available"].mean() * 100
    print(f"Weekend availability: {weekend_avail:.1f}%")
    print(f"Weekday availability: {weekday_avail:.1f}%")
    print(f"Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    return df


def compute_occupancy_summary(df, city):
    print(f"\n--- Computing per-listing occupancy summary ---")

    summary = df.groupby("listing_id").agg(
        total_days=("available", "count"),
        available_days=("available", "sum"),
        booked_days=("available", lambda x: (~x).sum()),
    ).reset_index()

    summary["occupancy_rate"] = (
        summary["booked_days"] / summary["total_days"] * 100
    ).round(2)

    output_path = f"data/processed/{city}/occupancy_summary.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    summary.to_csv(output_path, index=False)

    print(f"Listings processed: {len(summary):,}")
    print(f"Median occupancy rate: {summary['occupancy_rate'].median():.1f}%")
    print(f"Mean occupancy rate: {summary['occupancy_rate'].mean():.1f}%")
    print(f"Saved occupancy summary to: {output_path}")

    return df


def save_clean_data(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\nSaved to: {path}")
    print(f"Final shape: {df.shape[0]:,} rows x {df.shape[1]} columns")


# =============================================================================
# MAIN
# =============================================================================

def main(city):
    config = get_config(city)

    print("=" * 60)
    print("MILESTONE 3: DATA CLEANING — CALENDAR")
    print(f"City: {city.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    df = load_data(config["input_file"])
    df = drop_empty_columns(df)
    df = clean_availability(df)
    df = derive_features(df)
    df = compute_occupancy_summary(df, city)
    save_clean_data(df, config["output_file"])

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", type=str, default="bangkok")
    args = parser.parse_args()
    main(args.city)
