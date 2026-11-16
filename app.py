"""Streamlit dashboard for Kenya's mapped health-facility inventory.

This app intentionally reports mapped facility coverage and tag completeness.
It does not calculate or predict outbreak readiness because facility-level
readiness assessment records are not part of the local project data.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    import geopandas as gpd
    import matplotlib.pyplot as plt
    import pandas as pd
except Exception as exc:  # provide an actionable message for binary package issues
    st.set_page_config(page_title="Kenya Facility Explorer", page_icon="+", layout="wide")
    st.error(
        "A data or plotting package could not be imported. Check the project "
        "environment and reinstall compatible versions of pandas, NumPy, "
        "GeoPandas, and Matplotlib."
    )
    st.exception(exc)
    st.stop()


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "Datasets"
OUTPUT_DIR = ROOT / "reports" / "crisp_dm"
FACILITY_OUTPUT = OUTPUT_DIR / "kenya_facilities_cleaned_inventory.geojson"
FACILITY_SOURCE = DATA_DIR / "kenya.geojson"
COUNTY_SOURCE = DATA_DIR / "kenya_counties.geojson"

st.set_page_config(
    page_title="Kenya Facility Explorer",
    page_icon="+",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --ink: #173b3a; --muted: #617675; --teal: #0f766e; --wash: #edf5f2; }
      .stApp { background: #f7faf9; }
      [data-testid="stSidebar"] { background: #edf5f2; }
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1440px; }
      h1, h2, h3 { color: var(--ink); }
      .eyebrow { color: var(--teal); font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
      .hero { padding: 1.2rem 0 .5rem 0; }
      .hero p { max-width: 780px; color: var(--muted); font-size: 1.05rem; }
      .notice { border-left: 4px solid #d69e2e; background: #fff8e8; padding: .9rem 1rem; border-radius: 4px; color: #654f21; }
      .small-muted { color: var(--muted); font-size: .9rem; }
      div[data-testid="stMetric"] { background: white; border: 1px solid #e3ece9; padding: 1rem; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading facility and county data…")
def load_project_data() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Read local files, normalize blanks, and assign each mapped facility to a county."""
    facility_path = FACILITY_OUTPUT if FACILITY_OUTPUT.exists() else FACILITY_SOURCE
    if not facility_path.exists():
        raise FileNotFoundError(
            f"Facility data not found. Expected {FACILITY_OUTPUT} or {FACILITY_SOURCE}. "
            "Run Outbreak_Readiness_CRISP_DM.ipynb first."
        )
    if not COUNTY_SOURCE.exists():
        raise FileNotFoundError(f"County boundaries not found: {COUNTY_SOURCE}")

    facilities = gpd.read_file(facility_path)
    counties = gpd.read_file(COUNTY_SOURCE)
    facilities.columns = [str(c).strip() for c in facilities.columns]
    counties.columns = [str(c).strip() for c in counties.columns]

    county_name_column = next(
        (c for c in counties.columns if c.casefold() in {"county", "county_name", "name_1"}),
        None,
    )
    if county_name_column is None:
        raise ValueError(f"Could not find a county-name column in {COUNTY_SOURCE.name}.")
    if facilities.crs is None or counties.crs is None:
        raise ValueError("Both facility and county files must declare a coordinate reference system.")

    # Empty tags represent unrecorded information, not zero capacity.
    text_columns = [
        c for c in facilities.columns
        if c != facilities.geometry.name
        and (pd.api.types.is_object_dtype(facilities[c]) or pd.api.types.is_string_dtype(facilities[c]))
    ]
    for column in text_columns:
        facilities[column] = facilities[column].astype("string").str.strip()
        facilities[column] = facilities[column].replace(r"^\s*$", pd.NA, regex=True)

    for column in ["amenity", "healthcare"]:
        if column in facilities.columns:
            facilities[column] = facilities[column].astype("string").str.casefold()

    if "beds" in facilities.columns:
        beds = pd.to_numeric(facilities["beds"], errors="coerce")
        facilities["beds"] = beds.mask(beds < 0)

    counties["county"] = counties[county_name_column].astype("string").str.strip()
    counties["county"] = counties["county"].replace(
        {"Keiyo-Marakwet": "Elgeyo-Marakwet", "Tharaka": "Tharaka-Nithi"}
    )
    if facilities.crs != counties.crs:
        counties = counties.to_crs(facilities.crs)

    county_polygons = counties[["county", counties.geometry.name]].copy()
    county_polygons = county_polygons.rename_geometry("county_geometry")
    facility_geometries = facilities[
        facilities.geometry.notna() & ~facilities.geometry.is_empty
    ].copy()

    facility_county = gpd.sjoin(
        facility_geometries,
        county_polygons.set_geometry("county_geometry"),
        how="left",
        predicate="within",
    ).drop(columns=["index_right"], errors="ignore")

    # Use the equal-area CRS for comparable county land-area values.
    county_area = counties[["county", counties.geometry.name]].to_crs("EPSG:6933")
    county_area["area_km2"] = county_area.geometry.area / 1_000_000
    counts = (
        facility_county.dropna(subset=["county"])
        .groupby("county")
        .size()
        .rename("mapped_facilities")
    )
    county_summary = county_polygons[["county", "county_geometry"]].copy()
    county_summary = county_summary.merge(county_area[["county", "area_km2"]], on="county", how="left")
    county_summary = county_summary.merge(counts, on="county", how="left")
    county_summary["mapped_facilities"] = county_summary["mapped_facilities"].fillna(0).astype(int)
    county_summary["mapped_facilities_per_km2"] = (
        county_summary["mapped_facilities"] / county_summary["area_km2"]
    )
    return facilities, facility_county, county_summary


def format_int(value: int | float) -> str:
    return f"{int(value):,}"


def show_county_map(counties: gpd.GeoDataFrame, *, title: str = "Mapped facilities by county") -> None:
    map_data = counties.to_crs("EPSG:4326")
    fig, ax = plt.subplots(figsize=(7.5, 8.5), facecolor="#f7faf9")
    map_data.plot(
        column="mapped_facilities",
        cmap="YlGnBu",
        linewidth=0.55,
        edgecolor="white",
        legend=True,
        legend_kwds={"label": "Mapped facility records", "shrink": 0.68},
        ax=ax,
        missing_kwds={"color": "#e5e7eb"},
    )
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color="#173b3a", pad=12)
    ax.set_axis_off()
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


try:
    facilities, facility_county, county_summary = load_project_data()
except Exception as exc:
    st.title("Kenya Facility Explorer")
    st.error("The local project data could not be loaded.")
    st.exception(exc)
    st.stop()

county_total = int(county_summary["county"].nunique())
facility_total = int(len(facilities))
assigned_total = int(facility_county["county"].notna().sum())
assignment_pct = (assigned_total / len(facility_county) * 100) if len(facility_county) else 0.0

st.sidebar.markdown("<div class='eyebrow'>Outbreak Readiness System</div>", unsafe_allow_html=True)
st.sidebar.title("Facility Explorer")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "County explorer", "Facility explorer", "Data quality & sources"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption("Current view: mapped facility coverage")
st.sidebar.caption("Assessment readiness scores are not available in the local data.")

st.markdown("<div class='hero'><div class='eyebrow'>Kenya · health facilities</div>", unsafe_allow_html=True)
st.title("Outbreak Readiness Explorer")
st.markdown(
    "Explore mapped health facilities by county, inspect recorded attributes, and see where the inventory is incomplete."
)
st.markdown(
    "<div class='notice'><strong>Readiness scores are not calculated here.</strong> "
    "The local facility extract is a map inventory, not a facility assessment. "
    "Missing tags mean ‘not recorded’, not ‘service unavailable’.</div>",
    unsafe_allow_html=True,
)

if page == "Overview":
    st.subheader("National inventory at a glance")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mapped facility records", format_int(facility_total))
    m2.metric("Counties in boundary file", format_int(county_total))
    m3.metric("Assigned to a county", f"{assignment_pct:.1f}%", f"{format_int(assigned_total)} records")
    m4.metric("Unmatched records", format_int(len(facility_county) - assigned_total))

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        show_county_map(county_summary)
    with right:
        st.subheader("Largest mapped counts")
        top_counties = county_summary.sort_values("mapped_facilities", ascending=False).head(12)
        fig, ax = plt.subplots(figsize=(7, 5.7))
        ax.barh(top_counties.sort_values("mapped_facilities")["county"],
                top_counties.sort_values("mapped_facilities")["mapped_facilities"],
                color="#17877e")
        ax.set_xlabel("Mapped records")
        ax.set_ylabel("")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.grid(axis="x", color="#e6eeeb", linewidth=0.8)
        ax.set_axisbelow(True)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.caption("Counts reflect mapping and tagging coverage; they are not population-adjusted capacity or readiness.")

    with st.expander("What this dashboard can and cannot tell you"):
        st.markdown(
            "This dashboard can summarize facility records and the tags recorded in the local HOTOSM extract. "
            "It cannot confirm whether a real facility exists, is operational, has enough staff or supplies, "
            "or is ready for a specific outbreak. Use the Ministry of Health facility assessment for those questions."
        )

elif page == "County explorer":
    st.subheader("County profile")
    county_names = sorted(county_summary["county"].dropna().astype(str).unique())
    selected_county = st.selectbox("Choose a county", county_names)
    county_record = county_summary.loc[county_summary["county"].eq(selected_county)].iloc[0]
    county_facilities = facility_county.loc[facility_county["county"].eq(selected_county)].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Mapped facility records", format_int(county_record["mapped_facilities"]))
    c2.metric("County area (approx.)", f"{county_record['area_km2']:,.0f} km²")
    c3.metric("Mapped records per km²", f"{county_record['mapped_facilities_per_km2']:.3f}")

    st.markdown("**Readiness score:** not available from the current mapped inventory.")
    left, right = st.columns([1, 1], gap="large")
    with left:
        one_county = county_summary.loc[county_summary["county"].eq(selected_county)]
        show_county_map(one_county, title=f"{selected_county} boundary")
    with right:
        if not county_facilities.empty:
            locations = county_facilities.geometry.representative_point()
            map_frame = pd.DataFrame({"lat": locations.y, "lon": locations.x})
            st.subheader("Mapped facility locations")
            st.map(map_frame, latitude="lat", longitude="lon", size=12, color="#0f766e")
        else:
            st.info("No facility records in this county were assigned by the spatial join.")

    if not county_facilities.empty:
        display_columns = [
            c for c in ["name", "amenity", "healthcare", "operator", "operational_status", "beds", "completeness"]
            if c in county_facilities.columns
        ]
        st.subheader("Facility records")
        st.dataframe(
            county_facilities[display_columns].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

elif page == "Facility explorer":
    st.subheader("Search the mapped facility inventory")
    f1, f2, f3 = st.columns([1, 1, 1.3])
    county_options = ["All counties"] + sorted(county_summary["county"].dropna().astype(str).unique())
    with f1:
        county_filter = st.selectbox("County", county_options)
    with f2:
        category_source = facilities["healthcare"].fillna(facilities.get("amenity", pd.Series(index=facilities.index, dtype="string")))
        category_options = ["All categories"] + sorted(category_source.dropna().astype(str).unique())
        category_filter = st.selectbox("Healthcare tag", category_options)
    with f3:
        search_text = st.text_input("Search facility name", placeholder="Type a facility name")

    filtered = facility_county.copy()
    if county_filter != "All counties":
        filtered = filtered.loc[filtered["county"].eq(county_filter)]
    if category_filter != "All categories":
        healthcare = filtered.get("healthcare", pd.Series(index=filtered.index, dtype="string"))
        amenity = filtered.get("amenity", pd.Series(index=filtered.index, dtype="string"))
        filtered = filtered.loc[healthcare.eq(category_filter) | (healthcare.isna() & amenity.eq(category_filter))]
    if search_text.strip() and "name" in filtered.columns:
        filtered = filtered.loc[
            filtered["name"].astype("string").str.contains(search_text.strip(), case=False, na=False)
        ]

    st.caption(f"{len(filtered):,} records match the selected filters.")
    if not filtered.empty:
        if len(filtered) > 1:
            locations = filtered.geometry.representative_point()
            st.map(pd.DataFrame({"lat": locations.y, "lon": locations.x}), latitude="lat", longitude="lon", size=10)
        display_columns = [
            c for c in ["name", "county", "amenity", "healthcare", "operator", "operator_type",
                        "operational_status", "beds", "emergency", "water_source", "electricity", "completeness"]
            if c in filtered.columns
        ]
        st.dataframe(filtered[display_columns].reset_index(drop=True), use_container_width=True, hide_index=True)

        export_frame = filtered[display_columns].copy()
        st.download_button(
            "Download filtered records as CSV",
            data=export_frame.to_csv(index=False).encode("utf-8"),
            file_name="kenya_mapped_facilities_filtered.csv",
            mime="text/csv",
        )
    else:
        st.info("No records match these filters.")

elif page == "Data quality & sources":
    st.subheader("Recorded attributes and missing data")
    st.markdown(
        "A blank field means the map record does not include that attribute. "
        "It does not establish that the service, equipment, or staff are absent."
    )
    missing_rows = []
    for column in facilities.columns:
        if column == facilities.geometry.name:
            continue
        missing_count = int(facilities[column].isna().sum())
        missing_rows.append({
            "Field": column,
            "Not recorded": missing_count,
            "Recorded": int(len(facilities) - missing_count),
            "Missing %": round(missing_count / len(facilities) * 100, 2) if len(facilities) else 0,
        })
    missing_frame = pd.DataFrame(missing_rows).sort_values("Missing %", ascending=False)
    st.dataframe(missing_frame, use_container_width=True, hide_index=True)
    st.download_button(
        "Download field completeness as CSV",
        data=missing_frame.to_csv(index=False).encode("utf-8"),
        file_name="kenya_facility_field_completeness.csv",
        mime="text/csv",
    )

    st.subheader("Sources and interpretation")
    st.markdown(
        "- Facility inventory: [HOTOSM Kenya Health Facilities on HDX](https://data.humdata.org/dataset/hotosm_ken_health_facilities)\n"
        "- County boundaries: local GeoJSON in `Datasets/kenya_counties.geojson`\n"
        "- Readiness reference: [Kenya Health Facility Census report (2023)](https://www.health.go.ke/sites/default/files/2024-01/Kenya%20Health%20Facility%20Census%20Report%20September%202023.pdf)\n"
        "- Assessment results: [Kenya Health Facility Assessment dashboard](https://cema.shinyapps.io/kenya-hfa-app/)\n"
        "- Newer assessment context: [QoC-HFA service availability/readiness report](https://health.go.ke/sites/default/files/2026-06/Main%20Report%20-%20SARA%2021.10.2025.pdf)"
    )
    st.info(
        "A validated 1–10 readiness score requires facility-level assessment data and a documented scoring rule. "
        "The local PDF reports are reference material, not row-level training data."
    )

st.sidebar.divider()
st.sidebar.caption("Data snapshot: local project files · county assignment is spatial")
