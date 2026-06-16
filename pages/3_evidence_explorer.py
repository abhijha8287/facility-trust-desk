import pandas as pd
import streamlit as st

from services.db import get_cached_scores, get_facility_detail
from utils.constants import CAPABILITIES, TRUST_COLORS, TRUST_ICONS
from utils.parsers import parse_array_field

st.set_page_config(page_title="Evidence Explorer", page_icon="🔬", layout="wide")

st.title("🔬 Evidence Explorer")
st.caption("Inspect every text snippet that drove each trust assessment.")

# ── Accept ?fid= URL param ────────────────────────────────────────────────────
url_fid = st.query_params.get("fid")
if url_fid and "selected_facility_id" not in st.session_state:
    st.session_state["selected_facility_id"] = url_fid

# ── Guard ─────────────────────────────────────────────────────────────────────
if "selected_facility_id" not in st.session_state:
    st.warning("← Go to **Facility Search** to select a facility first.")
    if st.button("Go to Search"):
        st.switch_page("pages/1_facility_search.py")
    st.stop()

facility_id = st.session_state["selected_facility_id"]

with st.spinner("Loading facility..."):
    facility = get_facility_detail(facility_id)

if facility is None:
    st.error(f"Facility `{facility_id}` not found.")
    st.stop()

st.subheader(facility.get("name", "Unknown Facility"))

# ── Raw source fields ─────────────────────────────────────────────────────────
with st.expander("📂 Raw Facility Data (all source fields)", expanded=False):
    source_fields = {
        "description":  facility.get("description") or "—",
        "specialties":  parse_array_field(facility.get("specialties")),
        "procedure":    parse_array_field(facility.get("procedure")),
        "equipment":    parse_array_field(facility.get("equipment")),
        "capability":   parse_array_field(facility.get("capability")),
    }
    for field, value in source_fields.items():
        st.markdown(f"**{field}**")
        if isinstance(value, list):
            if value:
                st.markdown("  \n".join(f"- {v}" for v in value))
            else:
                st.caption("_(none)_")
        else:
            st.write(value or "_(none)_")
        st.markdown("---")

st.divider()

# ── Trust score evidence ───────────────────────────────────────────────────────
cached = get_cached_scores(facility_id)
if not cached:
    st.info(
        "No trust assessment found for this facility. "
        "Go to **Trust Report** to generate one first."
    )
    if st.button("Go to Trust Report →", type="primary"):
        st.switch_page("pages/2_trust_report.py")
    st.stop()

cached_by_cap = {row["capability"]: row for row in cached}

st.subheader("Evidence by Capability")

for cap in CAPABILITIES:
    score = cached_by_cap.get(cap)
    if not score:
        continue

    trust = score.get("trust_level", "No Evidence")
    evidence = score.get("evidence", score.get("evidence_json", []))
    missing = score.get("missing_evidence", score.get("missing_evidence_json", []))
    reasoning = score.get("reasoning", "")
    source_fields_map: dict = score.get("source_fields", {})

    color = TRUST_COLORS.get(trust, "#6c757d")
    icon = TRUST_ICONS.get(trust, "❓")

    with st.expander(
        f"{icon} {cap}  —  {trust}  "
        f"({int(float(score.get('confidence_score', 0)) * 100)}% confidence)"
    ):
        if evidence:
            st.markdown("**Evidence Snippets:**")

            if source_fields_map:
                rows = [
                    {"Source Field": source_fields_map.get(e, "unknown"), "Matched Text": e}
                    for e in evidence
                ]
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                for e in evidence:
                    st.markdown(
                        f"> _{e}_",
                    )
        else:
            st.caption("_No supporting evidence found in the dataset._")

        if missing:
            st.markdown("**What would strengthen this assessment:**")
            for m in missing:
                st.markdown(f"- {m}")

        if reasoning:
            st.markdown("**AI Reasoning:**")
            st.markdown(
                f"<div style='background:#f8f9fa;padding:10px;border-radius:6px;"
                f"border-left:4px solid {color};'>{reasoning}</div>",
                unsafe_allow_html=True,
            )

st.divider()
nav_cols = st.columns(3)
with nav_cols[0]:
    if st.button("← Back to Search"):
        st.switch_page("pages/1_facility_search.py")
with nav_cols[1]:
    if st.button("📊 Trust Report"):
        st.switch_page("pages/2_trust_report.py")
with nav_cols[2]:
    if st.button("👤 Human Review Desk"):
        st.switch_page("pages/4_human_review.py")
