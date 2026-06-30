# =============================================================================
# Airbnb Market Analytics System
# Milestone 7: Streamlit Dashboard
# Usage: streamlit run dashboard/app.py
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json
import warnings
warnings.filterwarnings("ignore")

load_dotenv()

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Airbnb Market Intelligence",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# THEME & STYLES
# =============================================================================

st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0d1117; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* All text */
    .stApp, .stMarkdown, p, h1, h2, h3, label {
        color: #e6edf3 !important;
    }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-2px); }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 6px 0 2px 0;
        background: linear-gradient(90deg, #f97316, #fb923c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .kpi-value-blue {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 6px 0 2px 0;
        background: linear-gradient(90deg, #3b82f6, #60a5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .kpi-label {
        font-size: 0.82rem;
        color: #8b949e !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 500;
    }
    .kpi-delta {
        font-size: 0.78rem;
        color: #22c55e !important;
        margin-top: 2px;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #e6edf3 !important;
        border-left: 3px solid #f97316;
        padding-left: 12px;
        margin: 24px 0 16px 0;
    }

    /* Divider */
    .custom-divider {
        border: none;
        border-top: 1px solid #21262d;
        margin: 20px 0;
    }

    /* Metric delta override */
    [data-testid="stMetricDelta"] { color: #22c55e !important; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #161b22;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #8b949e;
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #e6edf3 !important;
    }

    /* Selectbox and slider */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: #e6edf3 !important;
    }

    /* Hide default streamlit elements */
    #MainMenu, footer, header { visibility: hidden; }

    /* Plotly chart background */
    .js-plotly-plot { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONSTANTS
# =============================================================================

COLORS = {
    "bangkok":  "#f97316",
    "lisbon":   "#3b82f6",
    "accent":   "#a78bfa",
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral":  "#8b949e",
    "bg":       "#0d1117",
    "card":     "#161b22",
    "border":   "#30363d",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#161b22",
    plot_bgcolor="#161b22",
    font=dict(color="#e6edf3", family="Inter, sans-serif"),
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickcolor="#8b949e"),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickcolor="#8b949e"),
    legend=dict(
        bgcolor="#1c2128",
        bordercolor="#30363d",
        borderwidth=1,
        font=dict(color="#e6edf3")
    ),
)

CITY_CURRENCY = {"bangkok": "฿", "lisbon": "€"}
CITY_CENTRE = {"bangkok": (13.7563, 100.5018), "lisbon": (38.7169, -9.1399)}

# =============================================================================
# DATABASE
# =============================================================================


@st.cache_resource
def get_engine():
    host = os.getenv("DB_HOST",     "localhost")
    port = os.getenv("DB_PORT",     "5432")
    name = os.getenv("DB_NAME",     "airbnb_analytics")
    user = os.getenv("DB_USER",     "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url)


@st.cache_data(ttl=300)
def query(_engine, sql, params=None):
    with _engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

# =============================================================================
# DATA LOADERS
# =============================================================================


@st.cache_data(ttl=300)
def load_listings(_engine, cities, room_types, price_min, price_max, min_nights_max):
    city_filter = "(" + ",".join([f"'{c}'" for c in cities]) + ")"
    room_filter = "(" + ",".join([f"'{r}'" for r in room_types]) + ")"
    sql = f"""
        SELECT f.listing_id, f.city, f.host_id, f.neighbourhood_cleansed,
               f.room_type, f.property_type, f.property_type_grouped,
               f.price, f.price_tier, f.price_per_bedroom,
               f.price_vs_neighbourhood,
               f.minimum_nights, f.maximum_nights,
               f.availability_365, f.number_of_reviews,
               f.review_scores_rating, f.review_scores_accuracy,
               f.review_scores_cleanliness, f.review_scores_checkin,
               f.review_scores_location, f.review_scores_communication,
               f.review_scores_value,
               f.review_score_composite, f.review_velocity,
               f.occupancy_rate, f.booked_days, f.available_days,
               f.estimated_annual_revenue,
               f.host_tenure_years, f.instant_bookable,
               f.calculated_host_listings_count,
               h.host_is_superhost, h.is_commercial_host,
               h.host_response_rate, h.host_acceptance_rate
        FROM fact_listings f
        LEFT JOIN dim_host h
               ON f.host_id = h.host_id AND f.city = h.city
        WHERE f.city IN {city_filter}
          AND f.room_type IN {room_filter}
          AND f.price BETWEEN {price_min} AND {price_max}
          AND f.minimum_nights <= {min_nights_max}
          AND f.price IS NOT NULL
    """
    return query(_engine, sql)


@st.cache_data(ttl=300)
def load_reviews(_engine, cities):
    city_filter = "(" + ",".join([f"'{c}'" for c in cities]) + ")"
    sql = f"""
        SELECT city, review_year, review_month, review_year_month,
               COUNT(*) as review_count
        FROM fact_reviews
        WHERE city IN {city_filter}
          AND review_year >= 2015
        GROUP BY city, review_year, review_month, review_year_month
        ORDER BY city, review_year, review_month
    """
    return query(_engine, sql)


@st.cache_data(ttl=300)
def load_calendar_monthly(_engine, cities):
    city_filter = "(" + ",".join([f"'{c}'" for c in cities]) + ")"
    sql = f"""
        SELECT city, month, is_weekend,
               AVG(CASE WHEN available THEN 1.0 ELSE 0.0 END) * 100 as availability_rate,
               COUNT(*) as total_days
        FROM fact_calendar
        WHERE city IN {city_filter}
        GROUP BY city, month, is_weekend
        ORDER BY city, month
    """
    return query(_engine, sql)


@st.cache_data(ttl=300)
def load_neighbourhood_stats(_engine, cities):
    city_filter = "(" + ",".join([f"'{c}'" for c in cities]) + ")"
    sql = f"""
        SELECT city, neighbourhood_cleansed,
               COUNT(*)                                    AS listing_count,
               ROUND(AVG(price)::numeric, 0)              AS avg_price,
               ROUND(PERCENTILE_CONT(0.5)
                     WITHIN GROUP (ORDER BY price)::numeric, 0) AS median_price,
               ROUND(AVG(review_scores_rating)::numeric, 3) AS avg_rating,
               ROUND(AVG(occupancy_rate)::numeric, 1)     AS avg_occupancy,
               ROUND(AVG(estimated_annual_revenue)::numeric, 0) AS avg_revenue
        FROM fact_listings
        WHERE city IN {city_filter}
          AND price IS NOT NULL
        GROUP BY city, neighbourhood_cleansed
        ORDER BY city, listing_count DESC
    """
    return query(_engine, sql)

# =============================================================================
# CHART HELPERS
# =============================================================================


def apply_layout(fig, title="", height=380):
    fig.update_layout(**PLOTLY_LAYOUT, title=title,
                      title_font=dict(size=13, color="#e6edf3"),
                      height=height)
    return fig


def city_color(city):
    return COLORS["bangkok"] if city == "bangkok" else COLORS["lisbon"]


def format_price(value, city):
    sym = CITY_CURRENCY.get(city, "$")
    if value >= 1_000_000:
        return f"{sym}{value/1_000_000:.1f}M"
    if value >= 1_000:
        return f"{sym}{value/1_000:.1f}K"
    return f"{sym}{value:,.0f}"

# =============================================================================
# KPI CARDS
# =============================================================================


def render_kpi_cards(df, cities):
    cols = st.columns(4)

    total = len(df)
    med_price_bkk = df[df["city"] == "bangkok"]["price"].median(
    ) if "bangkok" in cities else None
    med_price_lis = df[df["city"] == "lisbon"]["price"].median(
    ) if "lisbon" in cities else None
    mean_occ = df["occupancy_rate"].mean()
    avg_rating = df["review_scores_rating"].mean()

    with cols[0]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Listings</div>
            <div class="kpi-value">{total:,}</div>
            <div class="kpi-delta">
                {'🟠 BKK: ' + str(len(df[df['city'] == 'bangkok'])) + ' &nbsp; 🔵 LIS: ' + str(
                    len(df[df['city'] == 'lisbon'])) if len(cities) == 2 else ''}
            </div>
        </div>""", unsafe_allow_html=True)

    with cols[1]:
        if len(cities) == 1:
            city = cities[0]
            sym = CITY_CURRENCY[city]
            med_p = df["price"].median()
            color_cls = "kpi-value" if city == "bangkok" else "kpi-value-blue"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Median Price / Night</div>
                <div class="{color_cls}">{sym}{med_p:,.0f}</div>
                <div class="kpi-delta">per night</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Median Price / Night</div>
                <div class="kpi-value">฿{med_price_bkk:,.0f}</div>
                <div class="kpi-delta">🔵 Lisbon: €{med_price_lis:,.0f}</div>
            </div>""", unsafe_allow_html=True)

    with cols[2]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Mean Occupancy Rate</div>
            <div class="kpi-value">{mean_occ:.1f}%</div>
            <div class="kpi-delta">of 365 calendar days</div>
        </div>""", unsafe_allow_html=True)

    with cols[3]:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Avg Review Score</div>
            <div class="kpi-value-blue">{avg_rating:.3f}</div>
            <div class="kpi-delta">out of 5.0</div>
        </div>""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding: 16px 0 8px 0;">
            <span style="font-size:2rem;">🏠</span>
            <h2 style="color:#e6edf3; margin:4px 0 0 0; font-size:1.1rem;">
                Airbnb Market Intelligence
            </h2>
            <p style="color:#8b949e; font-size:0.75rem; margin:2px 0 0 0;">
                Bangkok & Lisbon Analysis
            </p>
        </div>
        <hr style="border-color:#30363d; margin:12px 0;">
        """, unsafe_allow_html=True)

        st.markdown("**🌍 City Selection**")
        city_options = {"Bangkok 🟠": "bangkok",
                        "Lisbon 🔵":  "lisbon",
                        "Both Cities": "both"}
        city_choice = st.selectbox("", list(city_options.keys()),
                                   index=2, label_visibility="collapsed")
        selected_cities = (["bangkok", "lisbon"]
                           if city_options[city_choice] == "both"
                           else [city_options[city_choice]])

        st.markdown("<hr style='border-color:#30363d;'>",
                    unsafe_allow_html=True)
        st.markdown("**🛏 Room Types**")
        all_room_types = ["Entire home/apt", "Private room",
                          "Hotel room", "Shared room"]
        selected_rooms = st.multiselect("", all_room_types,
                                        default=all_room_types,
                                        label_visibility="collapsed")
        if not selected_rooms:
            selected_rooms = all_room_types

        st.markdown("<hr style='border-color:#30363d;'>",
                    unsafe_allow_html=True)
        st.markdown("**💰 Price Range**")

        if "bangkok" in selected_cities and "lisbon" in selected_cities:
            price_label = "฿ / €"
            p_max = 10000
        elif "bangkok" in selected_cities:
            price_label = "฿ THB"
            p_max = 10000
        else:
            price_label = "€ EUR"
            p_max = 1000

        price_range = st.slider(f"{price_label}",
                                min_value=0, max_value=p_max,
                                value=(0, p_max), step=50,
                                label_visibility="collapsed")

        st.markdown("<hr style='border-color:#30363d;'>",
                    unsafe_allow_html=True)
        st.markdown("**📅 Max Minimum Nights**")
        max_min_nights = st.slider("", min_value=1, max_value=365,
                                   value=365, step=1,
                                   label_visibility="collapsed")

        st.markdown("<hr style='border-color:#30363d;'>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center; padding: 8px 0;">
            <p style="color:#8b949e; font-size:0.7rem;">
                Data: Inside Airbnb<br>
                Bangkok (Sep 2025) · Lisbon (Mar 2026)<br>
                Built by Chathuri Samarasinghe
            </p>
        </div>
        """, unsafe_allow_html=True)

    return selected_cities, selected_rooms, price_range, max_min_nights

# =============================================================================
# TAB 1 — MARKET OVERVIEW
# =============================================================================


def tab_overview(df, cities, engine):
    st.markdown('<div class="section-header">Market Snapshot</div>',
                unsafe_allow_html=True)
    render_kpi_cards(df, cities)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    # --- Price Distribution ---
    with col1:
        st.markdown('<div class="section-header">Price Distribution</div>',
                    unsafe_allow_html=True)
        fig = go.Figure()
        for city in cities:
            city_df = df[df["city"] == city]
            cap = 10000 if city == "bangkok" else 1000
            prices = city_df["price"].dropna()
            prices = prices[prices <= cap]
            sym = CITY_CURRENCY[city]
            fig.add_trace(go.Histogram(
                x=prices, name=city.capitalize(),
                marker_color=city_color(city),
                opacity=0.75, nbinsx=80,
                hovertemplate=f"{sym}%{{x:,.0f}}<br>Count: %{{y}}<extra></extra>"
            ))
            fig.add_vline(x=float(prices.median()),
                          line_dash="dash", line_color=city_color(city),
                          annotation_text=f"Median {sym}{prices.median():,.0f}",
                          annotation_font_color=city_color(city))

        fig.update_layout(**PLOTLY_LAYOUT,
                          barmode="overlay",
                          title="Price per Night Distribution",
                          height=380,
                          xaxis_title="Price per Night",
                          yaxis_title="Number of Listings")
        st.plotly_chart(fig, use_container_width=True)

    # --- Room Type Donut ---
    with col2:
        st.markdown('<div class="section-header">Room Type Breakdown</div>',
                    unsafe_allow_html=True)
        room_counts = df.groupby(
            ["city", "room_type"]).size().reset_index(name="count")

        if len(cities) == 1:
            fig = go.Figure(go.Pie(
                labels=room_counts["room_type"],
                values=room_counts["count"],
                hole=0.55,
                marker_colors=[COLORS["bangkok"], COLORS["accent"],
                               COLORS["positive"], COLORS["neutral"]],
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value:,} listings<br>%{percent}<extra></extra>"
            ))
            fig.add_annotation(text=f"<b>{len(df):,}</b><br>listings",
                               x=0.5, y=0.5, showarrow=False,
                               font=dict(size=14, color="#e6edf3"))
        else:
            from plotly.subplots import make_subplots
            fig = make_subplots(rows=1, cols=2, specs=[[{"type": "pie"}, {"type": "pie"}]],
                                subplot_titles=["Bangkok", "Lisbon"])
            for i, city in enumerate(["bangkok", "lisbon"]):
                c_data = room_counts[room_counts["city"] == city]
                fig.add_trace(go.Pie(
                    labels=c_data["room_type"], values=c_data["count"],
                    hole=0.5, name=city.capitalize(),
                    marker_colors=[city_color(city), COLORS["accent"],
                                   COLORS["positive"], COLORS["neutral"]],
                    textinfo="label+percent",
                    hovertemplate="%{label}<br>%{value:,}<extra></extra>"
                ), row=1, col=i+1)

        fig.update_layout(**PLOTLY_LAYOUT, height=380,
                          title="Room Type Distribution",
                          showlegend=len(cities) == 1)
        st.plotly_chart(fig, use_container_width=True)

    # --- Top Neighbourhoods ---
    st.markdown('<div class="section-header">Top 10 Neighbourhoods by Median Price</div>',
                unsafe_allow_html=True)

    neigh_stats = load_neighbourhood_stats(engine, tuple(cities))
    if len(cities) == 2:
        col3, col4 = st.columns(2)
        cols_to_use = [col3, col4]
        cities_to_show = cities
    else:
        col3 = st.columns(1)[0]
        cols_to_use = [col3]
        cities_to_show = [cities[0]]

    for col, city in zip(cols_to_use, cities_to_show):
        with col:
            sym = CITY_CURRENCY[city]
            top10 = (neigh_stats[neigh_stats["city"] == city]
                     .nlargest(10, "median_price")
                     .sort_values("median_price", ascending=True))
            fig = go.Figure(go.Bar(
                x=top10["median_price"],
                y=top10["neighbourhood_cleansed"],
                orientation="h",
                marker_color=city_color(city),
                opacity=0.85,
                text=[f"{sym}{p:,.0f} · {c} listings"
                      for p, c in zip(top10["median_price"],
                                      top10["listing_count"])],
                textposition="outside",
                hovertemplate=(f"<b>%{{y}}</b><br>"
                               f"Median Price: {sym}%{{x:,.0f}}<br>"
                               f"<extra></extra>")
            ))

            fig.update_layout(**PLOTLY_LAYOUT,
                              title=f"{city.capitalize()} — Median Price by Neighbourhood",
                              height=420,
                              xaxis_title=f"Median Price ({sym})",
                              yaxis_title="",
                              margin=dict(l=20, r=120, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # --- Property Type Bar ---
    st.markdown('<div class="section-header">Property Type Distribution</div>',
                unsafe_allow_html=True)
    prop_counts = (df.groupby(["city", "property_type_grouped"])
                   .size().reset_index(name="count"))
    fig = px.bar(prop_counts, x="property_type_grouped", y="count",
                 color="city", barmode="group",
                 color_discrete_map={"bangkok": COLORS["bangkok"],
                                     "lisbon":  COLORS["lisbon"]},
                 labels={"property_type_grouped": "Property Type",
                         "count": "Number of Listings",
                         "city": "City"})
    fig.update_layout(**PLOTLY_LAYOUT,
                      title="Listings by Property Type Group",
                      height=360)
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TAB 2 — GEOGRAPHIC ANALYSIS
# =============================================================================


def tab_geographic(df, cities, engine):
    st.markdown('<div class="section-header">Neighbourhood Intelligence</div>',
                unsafe_allow_html=True)

    neigh_stats = load_neighbourhood_stats(engine, tuple(cities))

    city_for_map = st.selectbox(
        "Select city for map:",
        [c.capitalize() for c in cities],
        key="map_city_select"
    )
    map_city = city_for_map.lower()

    col_map, col_stats = st.columns([2, 1])

    with col_map:
        try:
            geojson_path = f"data/processed/{map_city}/neighbourhoods_clean.geojson"
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)

            city_neigh = neigh_stats[neigh_stats["city"] == map_city]
            stats_dict = city_neigh.set_index(
                "neighbourhood_cleansed").to_dict("index")

            for feature in geojson_data["features"]:
                name = feature["properties"].get("neighbourhood", "")
                if name in stats_dict:
                    feature["properties"].update(stats_dict[name])
                else:
                    feature["properties"].update({
                        "listing_count": 0, "median_price": 0,
                        "avg_rating": None, "avg_occupancy": None
                    })

            centre = CITY_CENTRE[map_city]
            m = folium.Map(location=centre, zoom_start=11,
                           tiles="CartoDB dark_matter")

            prices = city_neigh["median_price"].dropna()
            from branca.colormap import LinearColormap
            colormap = LinearColormap(
                colors=["#1e3a5f", "#1d4ed8",
                        COLORS[map_city], COLORS["negative"]],
                vmin=float(prices.quantile(0.1)),
                vmax=float(prices.quantile(0.9)),
                caption=f"Median Price ({CITY_CURRENCY[map_city]})"
            )

            folium.GeoJson(
                geojson_data,
                style_function=lambda feat: {
                    "fillColor": (
                        colormap(feat["properties"].get("median_price", 0))
                        if feat["properties"].get("median_price", 0) > 0
                        else "#2d3748"
                    ),
                    "color": "#4a5568",
                    "weight": 1.5,
                    "fillOpacity": 0.75,
                },
                tooltip=folium.features.GeoJsonTooltip(
                    fields=["neighbourhood", "listing_count",
                            "median_price", "avg_rating", "avg_occupancy"],
                    aliases=["Neighbourhood:", "Listings:",
                             f"Median Price ({CITY_CURRENCY[map_city]}):",
                             "Avg Rating:", "Avg Occupancy (%):"],
                    style="""
                        background-color: #1a202c; color: #e2e8f0;
                        font-family: monospace; font-size: 12px;
                        border: 1px solid #4a5568; border-radius: 4px;
                        padding: 8px;
                    """
                )
            ).add_to(m)
            colormap.add_to(m)
            st_folium(m, width=700, height=500)

        except Exception as e:
            st.error(f"Map error: {e}")

    with col_stats:
        st.markdown('<div class="section-header">Neighbourhood Rankings</div>',
                    unsafe_allow_html=True)
        sym = CITY_CURRENCY[map_city]
        city_neigh_sorted = (neigh_stats[neigh_stats["city"] == map_city]
                             .sort_values("median_price", ascending=False)
                             .head(15).reset_index(drop=True))

        rank_metric = st.radio("Rank by:",
                               ["Median Price", "Listing Count",
                                "Avg Occupancy", "Avg Rating"],
                               key="rank_metric")

        rank_col_map = {
            "Median Price":   "median_price",
            "Listing Count":  "listing_count",
            "Avg Occupancy":  "avg_occupancy",
            "Avg Rating":     "avg_rating"
        }
        sort_col = rank_col_map[rank_metric]
        city_neigh_ranked = (neigh_stats[neigh_stats["city"] == map_city]
                             .sort_values(sort_col, ascending=False)
                             .head(10).reset_index(drop=True))

        for i, row in city_neigh_ranked.iterrows():
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            st.markdown(f"""
            <div style="background:#1c2128; border:1px solid #30363d;
                        border-radius:8px; padding:10px 14px; margin-bottom:6px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#e6edf3; font-size:0.85rem; font-weight:500;">
                        {medal} {row['neighbourhood_cleansed']}
                    </span>
                    <span style="color:{COLORS[map_city]}; font-weight:700; font-size:0.9rem;">
                        {sym}{row['median_price']:,.0f}
                    </span>
                </div>
                <div style="color:#8b949e; font-size:0.72rem; margin-top:3px;">
                    {row['listing_count']:,} listings ·
                    {row['avg_occupancy']:.1f}% occupancy ·
                    ⭐ {row['avg_rating']:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- Scatter: Price vs Occupancy by Neighbourhood ---
    st.markdown('<div class="section-header">Price vs Occupancy by Neighbourhood</div>',
                unsafe_allow_html=True)
    scatter_data = neigh_stats[
        (neigh_stats["city"].isin(cities)) &
        (neigh_stats["listing_count"] >= 5)
    ].copy()

    fig = px.scatter(
        scatter_data,
        x="median_price", y="avg_occupancy",
        color="city", size="listing_count",
        hover_name="neighbourhood_cleansed",
        color_discrete_map={"bangkok": COLORS["bangkok"],
                            "lisbon":  COLORS["lisbon"]},
        labels={
            "median_price":  "Median Price per Night",
            "avg_occupancy": "Average Occupancy Rate (%)",
            "listing_count": "Listing Count",
            "city": "City"
        },
        size_max=40,
        hover_data={"avg_rating": ":.2f",
                    "listing_count": ":,",
                    "city": False}
    )
    fig.update_layout(**PLOTLY_LAYOUT,
                      title="Neighbourhood: Price vs Occupancy (bubble size = listing count)",
                      height=420)
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TAB 3 — HOST INTELLIGENCE
# =============================================================================


def tab_hosts(df, cities):
    st.markdown('<div class="section-header">Host Market Analysis</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # --- Superhost Comparison ---
    with col1:
        st.markdown('<div class="section-header">Superhost Performance</div>',
                    unsafe_allow_html=True)
        sh_data = []
        for city in cities:
            cdf = df[df["city"] == city]
            for sh_val, label in [(True, "Superhost"), (False, "Non-Superhost")]:
                subset = cdf[cdf["host_is_superhost"] == sh_val]
                if len(subset) > 0:
                    sh_data.append({
                        "city": city.capitalize(), "type": label,
                        "median_price": subset["price"].median(),
                        "avg_occupancy": subset["occupancy_rate"].mean(),
                        "avg_rating": subset["review_scores_rating"].mean(),
                        "count": len(subset)
                    })
        sh_df = pd.DataFrame(sh_data)

        metric = st.radio("Compare by:", ["Avg Rating", "Avg Occupancy %", "Median Price"],
                          horizontal=True, key="sh_metric")
        col_map = {"Avg Rating": "avg_rating",
                   "Avg Occupancy %": "avg_occupancy",
                   "Median Price": "median_price"}

        fig = px.bar(sh_df, x="city", y=col_map[metric], color="type",
                     barmode="group",
                     color_discrete_map={"Superhost": COLORS["accent"],
                                         "Non-Superhost": COLORS["neutral"]},
                     text_auto=".2f",
                     labels={"city": "City", col_map[metric]: metric, "type": ""})
        fig.update_layout(**PLOTLY_LAYOUT, height=360,
                          title=f"Superhost vs Non-Superhost — {metric}")
        st.plotly_chart(fig, use_container_width=True)

        for row in sh_data:
            if row["type"] == "Superhost":
                nsh = next((r for r in sh_data
                            if r["city"] == row["city"]
                            and r["type"] == "Non-Superhost"), None)
                if nsh:
                    diff = row["avg_rating"] - nsh["avg_rating"]
                    st.metric(
                        label=f"{row['city']} Superhost Rating Advantage",
                        value=f"{row['avg_rating']:.3f}",
                        delta=f"+{diff:.3f} vs Non-Superhost"
                    )

    # --- Commercial vs Casual ---
    with col2:
        st.markdown('<div class="section-header">Commercial vs Casual Hosts</div>',
                    unsafe_allow_html=True)

        host_data = []
        for city in cities:
            cdf = df[df["city"] == city]
            for comm_val, label in [(True, "Commercial (>1 listing)"),
                                    (False, "Casual (1 listing)")]:
                subset = cdf[cdf["is_commercial_host"] == comm_val]
                if len(subset) > 0:
                    host_data.append({
                        "city": city.capitalize(), "type": label,
                        "count": len(subset),
                        "pct": len(subset) / len(cdf) * 100,
                        "median_price": subset["price"].median(),
                        "avg_occupancy": subset["occupancy_rate"].mean(),
                        "avg_rating": subset["review_scores_rating"].mean()
                    })
        host_df = pd.DataFrame(host_data)

        fig = px.bar(host_df, x="city", y="pct", color="type",
                     barmode="stack", text=host_df["pct"].round(1).astype(str) + "%",
                     color_discrete_map={
                         "Commercial (>1 listing)": COLORS["negative"],
                         "Casual (1 listing)":      COLORS["positive"]
                     },
                     labels={"city": "City", "pct": "% of Listings", "type": ""})
        fig.update_layout(**PLOTLY_LAYOUT, height=220,
                          title="Commercial vs Casual Host Share")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Performance Comparison</div>',
                    unsafe_allow_html=True)
        perf_metric = st.radio("Compare by:",
                               ["Avg Occupancy %", "Median Price", "Avg Rating"],
                               horizontal=True, key="host_metric")
        col_map2 = {"Avg Occupancy %": "avg_occupancy",
                    "Median Price": "median_price",
                    "Avg Rating": "avg_rating"}
        fig2 = px.bar(host_df, x="city", y=col_map2[perf_metric], color="type",
                      barmode="group", text_auto=".1f",
                      color_discrete_map={
                          "Commercial (>1 listing)": COLORS["negative"],
                          "Casual (1 listing)":      COLORS["positive"]
        },
            labels={"city": "City",
                    col_map2[perf_metric]: perf_metric, "type": ""})
        fig2.update_layout(**PLOTLY_LAYOUT, height=250,
                           title=f"Commercial vs Casual — {perf_metric}")
        st.plotly_chart(fig2, use_container_width=True)

    # --- Market Concentration ---
    st.markdown('<div class="section-header">Market Concentration — Power Law</div>',
                unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    for col, city in zip([col3, col4] if len(cities) == 2 else [col3], cities):
        with col:
            cdf = df[df["city"] == city]
            host_counts = (cdf.groupby("host_id")["listing_id"]
                           .count().reset_index(name="listing_count"))

            bins = [1, 2, 3, 5, 10, 20, 50, 100, 9999]
            labels = ["1", "2", "3-4", "5-9",
                      "10-19", "20-49", "50-99", "100+"]

            host_counts["bucket"] = pd.cut(
                host_counts["listing_count"],
                bins=bins, labels=labels, right=True
            )
            bucket_df = (host_counts["bucket"]
                         .value_counts()
                         .sort_index()
                         .reset_index())
            bucket_df.columns = ["Portfolio Size", "Host Count"]

            fig = px.bar(bucket_df, x="Portfolio Size", y="Host Count",
                         color_discrete_sequence=[city_color(city)],
                         text="Host Count")
            fig.update_traces(textposition="outside", opacity=0.85)
            fig.update_layout(**PLOTLY_LAYOUT,
                              title=f"{city.capitalize()} — Host Portfolio Distribution",
                              height=320,
                              xaxis_title="Number of Listings per Host",
                              yaxis_title="Number of Hosts")
            st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TAB 4 — TEMPORAL TRENDS
# =============================================================================


def tab_temporal(df, cities, engine):
    st.markdown('<div class="section-header">Temporal & Seasonal Analysis</div>',
                unsafe_allow_html=True)

    reviews_data = load_reviews(engine, tuple(cities))
    calendar_data = load_calendar_monthly(engine, tuple(cities))

    col1, col2 = st.columns(2)

    # --- Review Volume Trend ---
    with col1:
        yearly = (reviews_data.groupby(["city", "review_year"])["review_count"]
                  .sum().reset_index())
        fig = go.Figure()
        for city in cities:
            city_data = yearly[yearly["city"] == city]
            fig.add_trace(go.Scatter(
                x=city_data["review_year"],
                y=city_data["review_count"],
                name=city.capitalize(),
                mode="lines+markers",
                line=dict(color=city_color(city), width=2.5),
                marker=dict(size=7),
                fill="tozeroy",
                fillcolor=city_color(city).replace(
                    ")", ",0.1)").replace("rgb", "rgba")
                if "rgb" in city_color(city) else city_color(city),
                hovertemplate=f"{city.capitalize()}<br>Year: %{{x}}<br>"
                f"Reviews: %{{y:,}}<extra></extra>"
            ))
            # COVID annotation
            covid_row = city_data[city_data["review_year"] == 2020]
            if not covid_row.empty:
                fig.add_annotation(
                    x=2020, y=float(covid_row["review_count"].iloc[0]),
                    text="COVID-19", showarrow=True,
                    arrowhead=2, arrowcolor="#ef4444",
                    font=dict(color="#ef4444", size=10),
                    ax=30, ay=-40
                )

        fig.update_layout(**PLOTLY_LAYOUT,
                          title="Annual Review Volume (Booking Demand Proxy)",
                          height=380,
                          xaxis_title="Year",
                          yaxis_title="Number of Reviews")
        fig.update_yaxes(tickformat=".0s")
        st.plotly_chart(fig, use_container_width=True)

    # --- Monthly Availability ---
    with col2:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        cal_monthly = (calendar_data.groupby(["city", "month"])["availability_rate"]
                       .mean().reset_index())

        fig = go.Figure()
        for city in cities:
            city_cal = cal_monthly[cal_monthly["city"]
                                   == city].sort_values("month")
            fig.add_trace(go.Scatter(
                x=city_cal["month"],
                y=city_cal["availability_rate"],
                name=city.capitalize(),
                mode="lines+markers",
                line=dict(color=city_color(city), width=2.5),
                marker=dict(size=7),
                hovertemplate=(f"{city.capitalize()}<br>Month: %{{x}}<br>"
                               f"Availability: %{{y:.1f}}%<extra></extra>")
            ))

        fig.update_layout(**PLOTLY_LAYOUT,
                          title="Monthly Availability Rate",
                          height=380,
                          xaxis_title="Month",
                          yaxis_title="Availability Rate (%)")
        fig.update_xaxes(tickmode="array",
                         tickvals=list(range(1, 13)),
                         ticktext=month_names)
        st.plotly_chart(fig, use_container_width=True)

    # --- Weekend vs Weekday ---
    col3, col4 = st.columns(2)
    with col3:
        weekend_data = (calendar_data.groupby(["city", "is_weekend"])
                        ["availability_rate"].mean().reset_index())
        weekend_data["day_type"] = weekend_data["is_weekend"].map(
            {True: "Weekend", False: "Weekday"})

        fig = px.bar(weekend_data, x="city", y="availability_rate",
                     color="day_type", barmode="group",
                     color_discrete_map={"Weekend": COLORS["accent"],
                                         "Weekday": COLORS["neutral"]},
                     text_auto=".1f",
                     labels={"city": "City",
                             "availability_rate": "Availability Rate (%)",
                             "day_type": ""})
        fig.update_layout(**PLOTLY_LAYOUT,
                          title="Weekend vs Weekday Availability",
                          height=340)
        st.plotly_chart(fig, use_container_width=True)

    # --- Occupancy Distribution ---
    with col4:
        fig = go.Figure()
        for city in cities:
            occ = df[df["city"] == city]["occupancy_rate"].dropna()
            fig.add_trace(go.Histogram(
                x=occ, name=city.capitalize(),
                marker_color=city_color(city),
                opacity=0.75, nbinsx=50,
                hovertemplate=f"Occupancy: %{{x:.1f}}%<br>Count: %{{y}}<extra></extra>"
            ))
            fig.add_vline(
                x=float(occ.median()),
                line_dash="dash", line_color=city_color(city),
                annotation_text=f"Median {occ.median():.1f}%",
                annotation_font_color=city_color(city)
            )
        fig.update_layout(**PLOTLY_LAYOUT, barmode="overlay",
                          title="Occupancy Rate Distribution",
                          height=340,
                          xaxis_title="Occupancy Rate (%)",
                          yaxis_title="Number of Listings")
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TAB 5 — PRICING INTELLIGENCE
# =============================================================================


def tab_pricing(df, cities):
    st.markdown('<div class="section-header">Pricing Intelligence</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # --- Price Tier Analysis ---
    with col1:
        tier_order = ["Budget", "Mid-range", "Premium"]
        tier_colors = [COLORS["positive"],
                       COLORS["accent"], COLORS["negative"]]
        tier_data = []
        for city in cities:
            cdf = df[df["city"] == city]
            for tier in tier_order:
                t = cdf[cdf["price_tier"] == tier]
                if len(t) > 0:
                    tier_data.append({
                        "city": city.capitalize(), "tier": tier,
                        "count": len(t),
                        "avg_occupancy": t["occupancy_rate"].mean(),
                        "median_revenue": t["estimated_annual_revenue"].median()
                    })
        tier_df = pd.DataFrame(tier_data)

        tier_metric = st.radio("Show:",
                               ["Listing Count", "Avg Occupancy %",
                                "Median Annual Revenue"],
                               horizontal=True, key="tier_metric")
        t_col_map = {
            "Listing Count": "count",
            "Avg Occupancy %": "avg_occupancy",
            "Median Annual Revenue": "median_revenue"
        }
        fig = px.bar(tier_df, x="tier", y=t_col_map[tier_metric],
                     color="city", barmode="group",
                     category_orders={"tier": tier_order},
                     color_discrete_map={"Bangkok": COLORS["bangkok"],
                                         "Lisbon":  COLORS["lisbon"]},
                     text_auto=".0f",
                     labels={"tier": "Price Tier",
                             t_col_map[tier_metric]: tier_metric,
                             "city": "City"})
        fig.update_layout(**PLOTLY_LAYOUT,
                          title=f"Price Tier Analysis — {tier_metric}",
                          height=380)
        st.plotly_chart(fig, use_container_width=True)

    # --- Price by Room Type Box ---
    with col2:
        fig = go.Figure()
        for city in cities:
            cdf = df[df["city"] == city]
            cap = 10000 if city == "bangkok" else 1000
            cdf = cdf[cdf["price"] <= cap]
            for room in ["Entire home/apt", "Private room",
                         "Hotel room", "Shared room"]:
                subset = cdf[cdf["room_type"] == room]["price"].dropna()
                if len(subset) > 10:
                    fig.add_trace(go.Box(
                        y=subset,
                        name=f"{city.capitalize()[:3]} - {room[:10]}",
                        marker_color=city_color(city),
                        opacity=0.8,
                        boxmean=True,
                        hovertemplate=(f"<b>{city} — {room}</b><br>"
                                       f"Median: %{{median:.0f}}<br>"
                                       f"<extra></extra>")
                    ))
        fig.update_layout(**PLOTLY_LAYOUT,
                          title="Price Distribution by Room Type",
                          height=380,
                          xaxis_title="City — Room Type",
                          yaxis_title="Price per Night",
                          showlegend=False)
        fig.update_xaxes(tickangle=15)
        st.plotly_chart(fig, use_container_width=True)

    # --- Price vs Review Score Scatter ---
    st.markdown('<div class="section-header">Price vs Review Score Relationship</div>',
                unsafe_allow_html=True)
    sample = df[
        df["price"].notna() &
        df["review_scores_rating"].notna() &
        df["occupancy_rate"].notna()
    ].copy()
    for city in ["bangkok", "lisbon"]:
        cap = 8000 if city == "bangkok" else 800
        sample = sample[~((sample["city"] == city) & (sample["price"] > cap))]

    sample_plot = sample.sample(min(3000, len(sample)), random_state=42)
    fig = px.scatter(
        sample_plot,
        x="review_scores_rating",
        y="price",
        color="city",
        size="occupancy_rate",
        opacity=0.5,
        color_discrete_map={"bangkok": COLORS["bangkok"],
                            "lisbon":  COLORS["lisbon"]},
        labels={
            "review_scores_rating": "Review Score Rating",
            "price": "Price per Night",
            "occupancy_rate": "Occupancy Rate (%)",
            "city": "City"
        },
        hover_data={"neighbourhood_cleansed": True,
                    "room_type": True,
                    "occupancy_rate": ":.1f"}
    )
    fig.update_layout(**PLOTLY_LAYOUT,
                      title="Price vs Review Score (size = occupancy rate)",
                      height=420)
    st.plotly_chart(fig, use_container_width=True)

    # --- Review Sub-Dimensions ---
    st.markdown('<div class="section-header">Review Sub-Dimension Comparison</div>',
                unsafe_allow_html=True)
    sub_dims = ["review_scores_accuracy", "review_scores_cleanliness",
                "review_scores_checkin", "review_scores_communication",
                "review_scores_location", "review_scores_value"]
    dim_labels = ["Accuracy", "Cleanliness", "Check-in",
                  "Communication", "Location", "Value"]

    fig = go.Figure()
    for city in cities:
        cdf = df[df["city"] == city]
        means = [cdf[col].mean() for col in sub_dims]
        fig.add_trace(go.Scatterpolar(
            r=means + [means[0]],
            theta=dim_labels + [dim_labels[0]],
            fill="toself",
            name=city.capitalize(),
            line_color=city_color(city),
            fillcolor=city_color(city),
            opacity=0.3
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Review Sub-Dimension Radar Chart",
        height=420,
        polar=dict(
            bgcolor="#161b22",
            radialaxis=dict(
                visible=True, range=[4.0, 5.1],
                gridcolor="#30363d", tickcolor="#8b949e",
                tickfont=dict(color="#8b949e")
            ),
            angularaxis=dict(
                gridcolor="#30363d",
                tickfont=dict(color="#e6edf3")
            )
        )
    )
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# MAIN APP
# =============================================================================


def main():
    engine = get_engine()

    selected_cities, selected_rooms, price_range, max_min_nights = render_sidebar()

    df = load_listings(
        engine, tuple(selected_cities), tuple(selected_rooms),
        price_range[0], price_range[1], max_min_nights
    )

    if df.empty:
        st.warning(
            "No listings match the current filters. Please adjust the sidebar.")
        return

    # --- Header ---
    st.markdown(f"""
    <div style="padding: 0; margin-top: -60px;">
        <h1 style="color:#e6edf3; font-size:1.8rem; font-weight:700; margin:0;">
            🏠 Airbnb Market Intelligence Dashboard
        </h1>
        <p style="color:#8b949e; margin:4px 0 0 0; font-size:0.9rem;">
            Comparative analysis · Bangkok (Sep 2025) & Lisbon (Mar 2026) ·
            {len(df):,} listings loaded
        </p>
    </div>
    <hr style="border-color:#21262d; margin:8px 0 20px 0;">
    """, unsafe_allow_html=True)

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Market Overview",
        "🗺️ Geographic",
        "👤 Host Intelligence",
        "📅 Temporal Trends",
        "💰 Pricing Intelligence"
    ])

    with tab1:
        tab_overview(df, selected_cities, engine)
    with tab2:
        tab_geographic(df, selected_cities, engine)
    with tab3:
        tab_hosts(df, selected_cities)
    with tab4:
        tab_temporal(df, selected_cities, engine)
    with tab5:
        tab_pricing(df, selected_cities)


if __name__ == "__main__":
    main()
