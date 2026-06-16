import streamlit as st

from services.db import (
    get_cached_scores,
    get_facility_detail,
    write_capability_score,
)
from services.trust_engine import batch_evaluate
from utils.constants import CAPABILITIES, TRUST_COLORS, TRUST_ICONS
from utils.formatters import trust_badge, confidence_label
from utils.parsers import parse_array_field

st.set_page_config(page_title="Trust Report", page_icon="📊", layout="wide")

st.title("📊 Facility Trust Report")

# ── Accept ?fid= URL param so URLs are shareable ─────────────────────────────
url_fid = st.query_params.get("fid")
if url_fid and "selected_facility_id" not in st.session_state:
    st.session_state["selected_facility_id"] = url_fid

# ── Guard: need a selected facility ──────────────────────────────────────────
if "selected_facility_id" not in st.session_state:
    st.warning("← Go to **Facility Search** to select a facility first.")
    if st.button("Go to Search"):
        st.switch_page("pages/1_facility_search.py")
    st.stop()

facility_id = st.session_state["selected_facility_id"]

with st.spinner("Loading facility..."):
    facility = get_facility_detail(facility_id)

if facility is None:
    st.error(f"Facility `{facility_id}` not found in the database.")
    st.stop()

# ── Facility header ───────────────────────────────────────────────────────────
st.subheader(facility.get("name", "Unknown Facility"))
meta_cols = st.columns(4)
meta_cols[0].metric("City", facility.get("address_city") or "—")
meta_cols[1].metric("State", facility.get("address_stateOrRegion") or "—")
meta_cols[2].metric("Capacity", f"{facility.get('capacity', '?')} beds")
meta_cols[3].metric("Doctors", str(facility.get("numberDoctors", "?")))

with st.expander("📋 Facility Description"):
    st.write(facility.get("description") or "_No description available._")
    listed_caps = parse_array_field(facility.get("capability"))
    if listed_caps:
        st.markdown("**Listed Capabilities:** " + " · ".join(listed_caps))

st.divider()

# ── Check cache ────────────────────────────────────────────────────────────────
cached = get_cached_scores(facility_id)
cached_by_cap = {row["capability"]: row for row in cached}
all_cached = all(cap in cached_by_cap for cap in CAPABILITIES)

if not all_cached:
    if st.button("🤖 Generate Trust Assessment", type="primary"):
        progress_slot = st.empty()
        with st.spinner("Running AI capability analysis (parallel, ~5-15s)..."):
            scores = batch_evaluate(facility, progress_placeholder=progress_slot)
        progress_slot.empty()

        # Write all results to cache
        for score in scores:
            write_capability_score(
                facility_id=facility_id,
                facility_name=facility.get("name", ""),
                capability=score["capability"],
                trust_level=score["trust_level"],
                confidence_score=score["confidence_score"],
                evidence=score["evidence"],
                missing_evidence=score["missing_evidence"],
                reasoning=score["reasoning"],
            )
            cached_by_cap[score["capability"]] = score

        st.success("Assessment complete and cached.")
        st.rerun()
    else:
        st.info("Click **Generate Trust Assessment** to analyse this facility's capabilities.")
        st.stop()

# ── Results grid ──────────────────────────────────────────────────────────────
st.subheader("Capability Trust Assessments")

cols = st.columns(2)
for i, cap in enumerate(CAPABILITIES):
    score = cached_by_cap.get(cap)
    col = cols[i % 2]

    with col:
        trust = score.get("trust_level", "No Evidence") if score else "No Evidence"
        conf = float(score.get("confidence_score", 0.0)) if score else 0.0
        evidence = score.get("evidence", score.get("evidence_json", [])) if score else []
        missing = score.get("missing_evidence", score.get("missing_evidence_json", [])) if score else []
        reasoning = score.get("reasoning", "") if score else ""

        color = TRUST_COLORS.get(trust, "#6c757d")
        icon = TRUST_ICONS.get(trust, "❓")

        with st.container(border=True):
            st.markdown(
                f"<h4 style='margin-bottom:4px'>{icon} {cap}</h4>"
                f"<span style='background:{color};color:white;padding:2px 10px;"
                f"border-radius:10px;font-size:0.82em;font-weight:600;'>{trust}</span>",
                unsafe_allow_html=True,
            )
            st.progress(conf, text=f"Confidence: {int(conf * 100)}% ({confidence_label(conf)})")

            if evidence:
                st.markdown("**Evidence:**")
                for e in evidence[:3]:
                    st.markdown(f"- _{e}_")

            if missing:
                st.markdown(
                    "<small style='color:#888'>**Gaps:** "
                    + " · ".join(missing[:2])
                    + "</small>",
                    unsafe_allow_html=True,
                )

            if reasoning:
                with st.expander("Reasoning"):
                    st.write(reasoning)

st.divider()
nav_cols = st.columns(3)
with nav_cols[0]:
    if st.button("← Back to Search"):
        st.switch_page("pages/1_facility_search.py")
with nav_cols[1]:
    if st.button("🔬 Evidence Explorer"):
        st.switch_page("pages/3_evidence_explorer.py")
with nav_cols[2]:
    if st.button("👤 Human Review Desk"):
        st.switch_page("pages/4_human_review.py")
