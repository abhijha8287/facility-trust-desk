"""Facility Trust Desk — Streamlit entry point.

Handles:
- Page config and sidebar navigation
- Environment variable loading (.env for local dev, Streamlit secrets for Databricks Apps)
- One-time Delta table initialisation at startup
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Facility Trust Desk",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar branding
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/hospital.png",
        width=60,
    )
    st.markdown("## 🏥 Facility Trust Desk")
    st.caption(
        "Evidence-backed capability assessments for healthcare facilities."
    )
    st.divider()
    st.markdown("**Navigation**")
    st.page_link("pages/1_facility_search.py",    label="🔍 Facility Search")
    st.page_link("pages/2_trust_report.py",       label="📊 Trust Report")
    st.page_link("pages/3_evidence_explorer.py",  label="🔬 Evidence Explorer")
    st.page_link("pages/4_human_review.py",       label="👤 Human Review Desk")

    st.divider()
    if "selected_facility_id" in st.session_state:
        st.success(f"Selected: `{st.session_state['selected_facility_id'][:16]}…`")
    else:
        st.caption("No facility selected yet.")

# Initialise Delta tables once per session
if "tables_ready" not in st.session_state:
    with st.spinner("Initialising database tables..."):
        from services.db import init_tables
        init_tables()
    st.session_state["tables_ready"] = True

# Home page content
st.title("🏥 Facility Trust Desk")
st.markdown(
    """
    **Determine whether a healthcare facility can actually perform the services it claims.**

    Every trust assessment is backed by direct evidence from the facility's own records —
    no unsupported conclusions.

    ---

    ### How it works

    1. **Search** for a facility by name, city, or state.
    2. **Generate a Trust Report** — the AI analyses 7 critical capabilities and cites
       exact evidence from the dataset.
    3. **Explore the Evidence** — see which field (description, specialties, equipment…)
       each conclusion came from.
    4. **Human Review** — verify, reject, or annotate any assessment. All decisions are
       written to an auditable Delta table.

    ---

    ### Capabilities Evaluated
    """
)

from utils.constants import CAPABILITIES, TRUST_COLORS

cap_cols = st.columns(len(CAPABILITIES))
for col, cap in zip(cap_cols, CAPABILITIES):
    col.markdown(
        f"<div style='text-align:center;padding:8px;background:#f0f2f6;"
        f"border-radius:8px;font-size:0.85em;font-weight:600;'>{cap}</div>",
        unsafe_allow_html=True,
    )

st.divider()
st.markdown(
    """
    ### Trust Levels
    | Level | Meaning |
    |---|---|
    | ✅ **Strong Evidence** | Multiple independent signals confirm the capability |
    | ⚠️ **Partial Evidence** | Some signals present but gaps remain |
    | 🔶 **Weak Evidence** | One or two indirect mentions only |
    | ❌ **No Evidence** | Dataset contains nothing supporting the claim |
    """
)

st.divider()
if st.button("🔍 Start — Search for a Facility", type="primary", use_container_width=False):
    st.switch_page("pages/1_facility_search.py")
