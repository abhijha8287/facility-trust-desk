import pandas as pd
import streamlit as st

from services.db import get_distinct_cities, get_distinct_states, search_facilities

st.set_page_config(page_title="Facility Search", page_icon="🔍", layout="wide")

st.title("🔍 Facility Search")
st.caption("Search healthcare facilities and select one to generate a trust assessment.")

# ── Filters ──────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    name_query = st.text_input("Search by facility name", placeholder="e.g. General Hospital")

with col2:
    cities = get_distinct_cities()
    city_filter = st.selectbox("Filter by city", cities)

with col3:
    states = get_distinct_states()
    state_filter = st.selectbox("Filter by state / region", states)

search_clicked = st.button("Search", type="primary", use_container_width=False)

# ── Results ───────────────────────────────────────────────────────────────────
if search_clicked or name_query or city_filter or state_filter:
    with st.spinner("Searching facilities..."):
        rows = search_facilities(
            name_query=name_query,
            city_filter=city_filter or "",
            state_filter=state_filter or "",
        )

    if not rows:
        st.info("No facilities found. Try broadening your search.")
        st.stop()

    st.caption(f"Found {len(rows)} result(s). Click a row to select a facility.")

    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "unique_id": "ID",
        "name": "Name",
        "address_city": "City",
        "address_stateOrRegion": "State",
        "numberDoctors": "Doctors",
        "capacity": "Capacity (beds)",
    })

    display_cols = ["Name", "City", "State", "Doctors", "Capacity (beds)"]
    display_df = df[[c for c in display_cols if c in df.columns]]

    selection = st.dataframe(
        display_df,
        on_select="rerun",
        selection_mode="single-row",
        key="facility_table",
        use_container_width=True,
        hide_index=True,
    )

    selected_indices = selection.selection.rows
    if selected_indices:
        idx = selected_indices[0]
        facility_id = rows[idx]["unique_id"]
        facility_name = rows[idx]["name"]

        st.session_state["selected_facility_id"] = facility_id

        st.success(f"Selected: **{facility_name}**")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("📊 View Trust Report", type="primary", use_container_width=True):
                st.switch_page("pages/2_trust_report.py")
        with col_b:
            if st.button("🔬 Evidence Explorer", use_container_width=True):
                st.switch_page("pages/3_evidence_explorer.py")
        with col_c:
            if st.button("👤 Human Review Desk", use_container_width=True):
                st.switch_page("pages/4_human_review.py")
    elif "selected_facility_id" in st.session_state:
        st.info("Click a row in the table to select a facility.")
else:
    st.info("Enter a search term or select a filter and click **Search**.")
