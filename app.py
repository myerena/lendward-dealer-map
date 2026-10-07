"""Read-only dealer map. Refresh its data with prepare_data.py before deployment."""

import json
from datetime import date
from pathlib import Path

import streamlit as st
from streamlit_folium import st_folium

from geography import DATA_PATH, load_locations, search_places
from map_view import build_map, search_overlay

ROOT = Path(__file__).parent
st.set_page_config(page_title="Lendward | Dealer map", page_icon=":world_map:", layout="wide")

st.markdown("""<style>
    .block-container {padding-top:3.5rem;padding-bottom:1.5rem;max-width:1600px}
    h1 {color:#153a52;letter-spacing:-.035em}
    [data-testid="stSidebar"] {background:#f4f7f8}
    [data-testid="stMetricValue"] {color:#153a52;font-size:1.75rem}
    .eyebrow {color:#16798b;letter-spacing:.16em;font-size:12px;font-weight:700;margin-bottom:8px}
    @media (max-width: 640px) {
        [data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;gap:12px}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width:0!important;flex:1!important}
        [data-testid="stMetricLabel"] p {font-size:12px}
    }
</style>""", unsafe_allow_html=True)


@st.cache_data
def read_snapshot(modified_ns):
    return json.loads((ROOT / "data" / "map_data.json").read_text(encoding="utf-8"))


@st.cache_resource
def read_geography(modified_ns):
    return load_locations()


def readable_date(value):
    return date.fromisoformat(value).strftime("%b %d, %Y") if value else "Not provided"


snapshot_path = ROOT / "data" / "map_data.json"
if not snapshot_path.exists() or not DATA_PATH.exists():
    st.title("Dealer map")
    st.info("The dealer map is waiting for its first data import.")
    st.stop()

snapshot = read_snapshot(snapshot_path.stat().st_mtime_ns)
metadata, dealers = snapshot["metadata"], snapshot["dealers"]
zip_groups, cities = read_geography(DATA_PATH.stat().st_mtime_ns)

with st.sidebar:
    st.markdown('<div class="eyebrow">LENDWARD</div>', unsafe_allow_html=True)
    st.header("Find an area")
    with st.form("place_search"):
        query = st.text_input("City and state, or ZIP", placeholder="San Diego, CA")
        search = st.form_submit_button("Search map", use_container_width=True, type="primary")
    if search:
        st.session_state["place_results"] = search_places(query, zip_groups, cities)
        st.session_state["last_query"] = query.strip()
        st.session_state["search_revision"] = st.session_state.get("search_revision", 0) + 1
    results = st.session_state.get("place_results", [])
    place = None
    if results:
        selected = st.selectbox("Location", range(len(results)),
                                format_func=lambda i: results[i]["label"],
                                key=f"location_{st.session_state.get('search_revision', 0)}")
        place = results[selected]
    elif st.session_state.get("last_query"):
        st.info("No matching place. Try a city with its state, or a five-digit ZIP.")
    if st.button("Show all areas", use_container_width=True):
        st.session_state["place_results"] = []
        st.session_state["last_query"] = ""
        st.rerun()
    radius = st.selectbox("Distance rings", [0, 10, 25, 50], index=2,
                          format_func=lambda miles: f"Up to {miles} miles" if miles else "Off")
    st.caption("Rings show straight-line miles from the searched city or ZIP center, not driving distance.")
    st.divider()
    dealer_query = st.text_input("Find a dealer", placeholder="Dealer name")
    st.caption("Area search moves the map. Dealer search filters the pins.")
    st.divider()
    st.markdown("**Reading the map**")
    st.caption("Click a number to zoom in. Dealers sharing a ZIP spread apart when you click their group.")
    st.caption("Teal pins: dealer entries. Amber pins: names or locations awaiting review.")
    st.caption("Pins use approximate ZIP locations. They do not show mailing territories.")

shown = [d for d in dealers if dealer_query.casefold().strip() in d["dealer_name"].casefold()]
mapped = [d for d in shown if d["latitude"] is not None]
st.markdown('<div class="eyebrow">CAMPAIGN COVERAGE</div>', unsafe_allow_html=True)
st.title("Dealer map")
st.write("Explore the areas around your dealers before planning the next campaign.")
st.caption(f"Report updated {readable_date(metadata['report_as_of'])}  |  "
           f"Campaign drops: {readable_date(metadata['first_drop_date'])} to {readable_date(metadata['last_drop_date'])}")
metrics = st.columns(3)
metrics[0].metric("Dealer entries", f"{len(shown):,}")
metrics[1].metric("ZIP codes", f"{len({d['zip'] for d in mapped}):,}")
metrics[2].metric("Campaigns in report", f"{sum(d['campaign_count'] for d in shown):,}")
if place:
    st.markdown(f"**Viewing {place['label']}** - all dealer pins remain available as you pan or zoom.")
if not shown:
    st.info("No dealer names match this search. Clear the dealer search to restore all pins.")
center = (place["latitude"], place["longitude"]) if place else (38.8, -97.5)
zoom = ({0: 10, 10: 10, 25: 9, 50: 8}[radius] if place else 4)
st_folium(build_map(shown), height=565, use_container_width=True,
          center=center, zoom=zoom, feature_group_to_add=search_overlay(place, radius),
          returned_objects=[], key="dealer_map")
if missing := len(shown) - len(mapped):
    st.warning(f"{missing} entries cannot be placed by ZIP. They remain in the dealer list below.")
if metadata["review_count"]:
    st.caption(f"{metadata['review_count']} entries need review and remain separate. Open 'Entries needing review' below for details.")


def table_rows(entries, include_review=False):
    rows = []
    for dealer in entries:
        row = {"Dealer": dealer["dealer_name"], "State": dealer["state"], "ZIP": dealer["zip"],
               "Postal city": dealer["postal_city"], "Campaigns": dealer["campaign_count"],
               "Latest drop": dealer["latest_drop_date"],
               "Map status": "Mapped" if dealer["latitude"] is not None else "Not mapped"}
        if include_review:
            row.update({"Source dealer key": dealer["dealer_key"], "Review": dealer["review_note"]})
        rows.append(row)
    return rows


with st.expander(f"Browse dealer entries ({len(shown):,})"):
    st.dataframe(table_rows(shown), hide_index=True, width="stretch")
with st.expander(f"Entries needing review ({metadata['review_count']})"):
    st.dataframe(table_rows([d for d in dealers if d["review_note"]], True), hide_index=True, width="stretch")
st.caption("ZIP locations and city search: [GeoNames](https://www.geonames.org/), CC BY 4.0. "
           "Postal city names come from the ZIP lookup, not the campaign export.")
