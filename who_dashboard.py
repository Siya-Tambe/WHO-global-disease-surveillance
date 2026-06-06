
import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="WHO Global Disease Surveillance",
    page_icon="🌍",
    layout="wide"
)

# ── Load data ────────────────────────────────────────────────────
@st.cache_data
def load_data():
    conn = sqlite3.connect("/content/who_health.db")
    df = pd.read_sql_query("SELECT * FROM health_data", conn)
    conn.close()
    return df

@st.cache_data
def load_world():
    url = "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
    return gpd.read_file(url)

df = load_data()
world = load_world()

# ── Header ───────────────────────────────────────────────────────
st.title("WHO Global Disease Surveillance Dashboard")
st.markdown("Analysing health indicators across **203 countries** using WHO GHO API + SQL + Python")
st.markdown("---")

# ── Sidebar filters ──────────────────────────────────────────────
st.sidebar.header("Filters")

indicator = st.sidebar.selectbox(
    "Select Indicator",
    df["indicator_name"].unique()
)

year_min = int(df["year"].min())
year_max = int(df["year"].max())
selected_year = st.sidebar.slider("Select Year", year_min, year_max, 2021)

country = st.sidebar.selectbox(
    "Compare Country",
    sorted(df["country_code"].dropna().unique()),
    index=list(sorted(df["country_code"].dropna().unique())).index("IND")
)

# ── KPI Cards ────────────────────────────────────────────────────
st.subheader(f"{indicator} — {selected_year}")

filtered = df[(df["indicator_name"] == indicator) & (df["year"] == selected_year)]
country_val = filtered[filtered["country_code"] == country]["value"]
global_avg = filtered["value"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Countries with Data", len(filtered))
col2.metric("Global Average", f"{global_avg:.1f}")
col3.metric(
    f"{country} Value",
    f"{country_val.values[0]:.1f}" if len(country_val) > 0 else "N/A",
    delta=f"{(country_val.values[0] - global_avg):.1f} vs global" if len(country_val) > 0 else None
)
col4.metric("Year Range", f"{year_min} – {year_max}")

st.markdown("---")

# ── Row 1: World Map + Top 10 ─────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("World Map")
    map_data = filtered[
        filtered["region"].notna() &
        (filtered["country_code"].str.len() == 3) &
        (~filtered["country_code"].isin([
            "AFR","AMR","EMR","EUR","SEAR","WPR",
            "GLB","LMC","UMC","HIC","LIC","WLD"
        ]))
    ].groupby("country_code")["value"].mean().reset_index()

    world_merged = world.merge(
        map_data,
        left_on="ISO_A3",
        right_on="country_code",
        how="left"
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    world_merged.plot(
        column="value",
        ax=ax,
        legend=True,
        cmap="RdYlGn",
        missing_kwds={"color": "lightgrey"},
        legend_kwds={"shrink": 0.5}
    )
    ax.set_title(f"{indicator} by Country ({selected_year})", fontsize=12, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

with col_right:
    st.subheader("Top 10 Countries")
    top10 = filtered[
        filtered["region"].notna() &
        (~filtered["country_code"].isin([
            "AFR","AMR","EMR","EUR","SEAR","WPR",
            "GLB","LMC","UMC","HIC","LIC","WLD"
        ]))
    ].nlargest(10, "value")[["country_code", "region", "value"]]

    fig2, ax2 = plt.subplots(figsize=(6, 5))
    ax2.barh(top10["country_code"], top10["value"], color="steelblue")
    ax2.set_xlabel(indicator)
    ax2.set_title(f"Top 10 — {selected_year}")
    ax2.invert_yaxis()
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close()

st.markdown("---")

# ── Row 2: Trend + Regional comparison ───────────────────────────
col3a, col3b = st.columns(2)

with col3a:
    st.subheader(f"{country} Trend Over Time")
    trend = df[
        (df["country_code"] == country) &
        (df["indicator_name"] == indicator) &
        (df["year"] >= 2000)
    ].sort_values("year")

    fig3, ax3 = plt.subplots(figsize=(7, 4))
    ax3.plot(trend["year"], trend["value"], marker="o", color="darkorange", linewidth=2)
    ax3.set_xlabel("Year")
    ax3.set_ylabel(indicator)
    ax3.set_title(f"{country} — {indicator} (2000–Present)")
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    st.pyplot(fig3)
    plt.close()

with col3b:
    st.subheader("Regional Comparison")
    region_data = filtered[filtered["region"].notna()].groupby("region")["value"].mean().reset_index()
    region_data = region_data.sort_values("value", ascending=False)

    fig4, ax4 = plt.subplots(figsize=(7, 4))
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(region_data)))
    ax4.bar(region_data["region"], region_data["value"], color=colors)
    ax4.set_xlabel("WHO Region")
    ax4.set_ylabel(f"Avg {indicator}")
    ax4.set_title(f"Regional Average — {selected_year}")
    plt.xticks(rotation=25, ha="right", fontsize=8)
    plt.tight_layout()
    st.pyplot(fig4)
    plt.close()

st.markdown("---")
st.caption("Data source: WHO Global Health Observatory (GHO) API | Built with Python + SQL + Streamlit")
