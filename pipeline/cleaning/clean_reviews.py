# =============================================================================
# Airbnb Market Analytics System
# Milestone 3: Data Cleaning — Reviews
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
        "input_file": f"data/raw/{city}/reviews.csv",
        "output_file": f"data/processed/{city}/reviews_clean.csv",
    }

# =============================================================================
# CLEANING FUNCTIONS
# =============================================================================


def load_data(path):
    print(f"Loading {path}...")
    df = pd.read_csv(path, low_memory=False)
    print(f"Loaded: {df.shape[0]:,} rows x {df.shape[1]} columns")
    return df


def parse_dates(df):
    print(f"\n--- Parsing date columns ---")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    nulls = df["date"].isnull().sum()
    print(f"date: parsed. Nulls: {nulls:,}")
    print(f"Date range: {df['date'].min().date()} → {df['date'].max().date()}")
    return df


def handle_missing(df):
    print(f"\n--- Handling missing values ---")

    before = len(df)
    null_comments = df["comments"].isnull().sum()
    print(f"Null comments: {null_comments:,} — dropping these rows")
    df = df.dropna(subset=["comments"])

    null_names = df["reviewer_name"].isnull().sum()
    print(f"Null reviewer names: {null_names:,} — filling with 'Anonymous'")
    df["reviewer_name"] = df["reviewer_name"].fillna("Anonymous")

    after = len(df)
    print(
        f"Rows before: {before:,} → after: {after:,} (dropped {before - after:,})")
    return df


def derive_features(df):
    print(f"\n--- Deriving calculated fields ---")

    df["review_year"] = df["date"].dt.year
    df["review_month"] = df["date"].dt.month
    df["review_year_month"] = df["date"].dt.to_period("M").astype(str)

    print(
        f"review_year: {df['review_year'].min()} → {df['review_year'].max()}")
    print(f"review_year_month: added for time series analysis")

    # Comment length as a quality proxy
    df["comment_length"] = df["comments"].str.len()
    print(f"comment_length: median={df['comment_length'].median():.0f} chars")

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
    print("MILESTONE 3: DATA CLEANING — REVIEWS")
    print(f"City: {city.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    df = load_data(config["input_file"])
    df = parse_dates(df)
    df = handle_missing(df)
    df = derive_features(df)
    save_clean_data(df, config["output_file"])

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", type=str, default="bangkok")
    args = parser.parse_args()
    main(args.city)
