# =============================================================================
# Airbnb Market Analytics System
# Milestone 4: Data Enrichment
# City: Configurable via --city argument
# Usage: python pipeline/enrichment/enrich_listings.py --city bangkok
#        python pipeline/enrichment/enrich_listings.py --city lisbon
# =============================================================================

import pandas as pd
import numpy as np
import os
import argparse
from datetime import datetime

# =============================================================================
# CITY-SPECIFIC CONFIGURATION
# Add a new entry here whenever you add a new city.
# =============================================================================

CITY_CONFIG = {
    "bangkok": {
        "scrape_date": pd.Timestamp("2025-09-27"),
        "currency":    "฿",
    },
    "lisbon": {
        "scrape_date": pd.Timestamp("2026-03-26"),
        "currency":    "€",
    },
}


# =============================================================================
# CONFIGURATION
# =============================================================================

def get_config(city):
    city_cfg = CITY_CONFIG.get(city, {})
    return {
        "city":               city,
        "scrape_date":        city_cfg.get("scrape_date", pd.Timestamp("2025-01-01")),
        "currency":           city_cfg.get("currency", "$"),
        "listings_file":      f"data/processed/{city}/listings_clean.csv",
        "occupancy_file":     f"data/processed/{city}/occupancy_summary.csv",
        "neighbourhoods_file": f"data/processed/{city}/neighbourhoods_clean.csv",
        "output_file":        f"data/processed/{city}/listings_enriched.csv",
    }


# =============================================================================
# ENRICHMENT FUNCTIONS
# =============================================================================

def load_data(config):
    print("Loading cleaned files...")

    listings = pd.read_csv(
        config["listings_file"],
        parse_dates=["last_scraped", "host_since", "first_review",
                     "last_review", "calendar_last_scraped"],
        low_memory=False
    )
    occupancy = pd.read_csv(config["occupancy_file"])
    neighbourhoods = pd.read_csv(config["neighbourhoods_file"])

    print(
        f"Listings:       {listings.shape[0]:,} rows x {listings.shape[1]} columns")
    print(
        f"Occupancy:      {occupancy.shape[0]:,} rows x {occupancy.shape[1]} columns")
    print(f"Neighbourhoods: {neighbourhoods.shape[0]:,} rows")

    return listings, occupancy, neighbourhoods


def join_occupancy(listings, occupancy):
    print(f"\n--- Joining occupancy data ---")

    before = len(listings)
    listings = listings.merge(
        occupancy[["listing_id", "total_days", "available_days",
                   "booked_days", "occupancy_rate"]],
        left_on="id",
        right_on="listing_id",
        how="left"
    ).drop(columns=["listing_id"])

    after = len(listings)
    matched = listings["occupancy_rate"].notna().sum()
    print(f"Rows before: {before:,} → after: {after:,}")
    print(f"Listings with occupancy data: {matched:,}")
    print(f"Median occupancy rate: {listings['occupancy_rate'].median():.1f}%")

    return listings


def add_neighbourhood_aggregates(listings):
    print(f"\n--- Computing neighbourhood-level aggregates ---")

    priced = listings[listings["price"].notna()]

    neighbourhood_stats = priced.groupby("neighbourhood_cleansed").agg(
        neighbourhood_median_price=("price",              "median"),
        neighbourhood_mean_price=("price",              "mean"),
        neighbourhood_listing_count=("id",                "count"),
        neighbourhood_avg_rating=("review_scores_rating", "mean"),
        neighbourhood_avg_occupancy=("occupancy_rate",    "mean"),
    ).round(2).reset_index()

    listings = listings.merge(
        neighbourhood_stats,
        on="neighbourhood_cleansed",
        how="left"
    )

    print(
        f"Neighbourhood aggregates added for {len(neighbourhood_stats)} neighbourhoods")
    print(f"Top 5 by median price:")
    top5 = neighbourhood_stats.nlargest(5, "neighbourhood_median_price")[
        ["neighbourhood_cleansed", "neighbourhood_median_price",
         "neighbourhood_listing_count"]
    ]
    for _, row in top5.iterrows():
        print(f"  {row['neighbourhood_cleansed']:<30} "
              f"{row['neighbourhood_median_price']:>10,.0f}  "
              f"({row['neighbourhood_listing_count']} listings)")

    return listings


def add_price_positioning(listings):
    print(f"\n--- Adding price positioning features ---")

    listings["price_vs_neighbourhood"] = (
        (listings["price"] - listings["neighbourhood_median_price"])
        / listings["neighbourhood_median_price"] * 100
    ).round(2)

    valid_prices = listings["price"].dropna()
    p25 = valid_prices.quantile(0.25)
    p75 = valid_prices.quantile(0.75)

    def price_tier(price):
        if pd.isna(price):
            return None
        elif price <= p25:
            return "Budget"
        elif price <= p75:
            return "Mid-range"
        else:
            return "Premium"

    listings["price_tier"] = listings["price"].apply(price_tier)

    tier_counts = listings["price_tier"].value_counts()
    for tier, count in tier_counts.items():
        print(f"  {tier}: {count:,} listings ({count/len(listings)*100:.1f}%)")

    return listings


def add_review_features(listings, scrape_date):
    print(f"\n--- Adding review-based features ---")

    # Use the city-specific scrape_date passed in — not a hardcoded date
    listings["listing_age_years"] = (
        (scrape_date - listings["first_review"]).dt.days / 365.25
    ).round(2)

    listings["review_velocity"] = np.where(
        listings["listing_age_years"] > 0,
        (listings["number_of_reviews"] /
         listings["listing_age_years"]).round(2),
        np.nan
    )

    review_cols = [
        "review_scores_rating", "review_scores_accuracy",
        "review_scores_cleanliness", "review_scores_checkin",
        "review_scores_communication", "review_scores_location",
        "review_scores_value"
    ]
    # Only average the columns that actually exist in this city's dataset
    available_review_cols = [c for c in review_cols if c in listings.columns]
    listings["review_score_composite"] = listings[available_review_cols].mean(
        axis=1).round(3)

    valid_velocity = listings["review_velocity"].notna().sum()
    print(f"review_velocity: computed for {valid_velocity:,} listings")
    print(
        f"review_score_composite: median={listings['review_score_composite'].median():.3f}")

    return listings


def add_revenue_estimate(listings, currency):
    print(f"\n--- Adding revenue estimate ---")

    listings["estimated_annual_revenue"] = (
        listings["price"] * listings["booked_days"]
    ).round(2)

    valid = listings["estimated_annual_revenue"].notna().sum()
    median_rev = listings["estimated_annual_revenue"].median()
    print(f"Estimated annual revenue: computed for {valid:,} listings")
    print(f"Median estimated revenue: {currency}{median_rev:,.0f}")

    return listings


def save_enriched(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\nSaved enriched listings to: {path}")
    print(f"Final shape: {df.shape[0]:,} rows x {df.shape[1]} columns")


# =============================================================================
# MAIN
# =============================================================================

def main(city):
    config = get_config(city)

    print("=" * 60)
    print("MILESTONE 4: DATA ENRICHMENT")
    print(f"City: {city.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    listings, occupancy, neighbourhoods = load_data(config)
    listings = join_occupancy(listings, occupancy)
    listings = add_neighbourhood_aggregates(listings)
    listings = add_price_positioning(listings)
    listings = add_review_features(listings, config["scrape_date"])
    listings = add_revenue_estimate(listings, config["currency"])
    save_enriched(listings, config["output_file"])

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich cleaned Airbnb listings with occupancy, neighbourhood, and review features."
    )
    parser.add_argument(
        "--city", type=str, default="bangkok",
        help="City name matching folder in data/processed/ (e.g. bangkok, lisbon)"
    )
    args = parser.parse_args()
    main(args.city)
