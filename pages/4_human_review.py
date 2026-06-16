import pandas as pd
import streamlit as st

from services.db import get_cached_scores, get_facility_detail, get_reviews, write_review
from utils.constants import CAPABILITIES, TRUST_COLORS, TRUST_ICONS

st.set_page_config(page_title="Human Review Desk", page_icon="👤", layout="wide")

st.title("👤 Human Review Desk")
st.caption(
    "Verify or reject AI-generated trust assessments. "
    "All decisions are written to the Delta table and auditable."
)

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

facility_name = facility.get("name", "Unknown Facility")
st.subheader(facility_name)

# ── Load trust scores for context ─────────────────────────────────────────────
cached = get_cached_scores(facility_id)
cached_by_cap = {row["capability"]: row for row in cached}

# ── Capability selector ────────────────────────────────────────────────────────
capability = st.selectbox("Select capability to review", CAPABILITIES)

# Show current AI assessment for context
if capability in cached_by_cap:
    score = cached_by_cap[capability]
    trust = score.get("trust_level", "No Evidence")
    conf = float(score.get("confidence_score", 0.0))
    icon = TRUST_ICONS.get(trust, "❓")
    color = TRUST_COLORS.get(trust, "#6c757d")

    st.markdown(
        f"<div style='background:#f8f9fa;padding:12px;border-radius:8px;"
        f"border-left:5px solid {color};margin-bottom:12px;'>"
        f"<b>AI Assessment for {capability}:</b> {icon} {trust} "
        f"({int(conf * 100)}% confidence)<br>"
        f"<small>{score.get('reasoning', '')}</small>"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.info(
        f"No AI assessment found for **{capability}**. "
        "Run **Trust Report** first to generate one."
    )

st.divider()

# ── Review form ───────────────────────────────────────────────────────────────
notes = st.text_area(
    "Review notes",
    placeholder="Add your clinical assessment, field observations, or context...",
    height=120,
)

btn_cols = st.columns(3)

with btn_cols[0]:
    if st.button("✅ Verify", type="primary", use_container_width=True):
        try:
            write_review(facility_id, capability, "verified", notes)
            st.success(f"**{capability}** marked as **Verified** and saved to Delta table.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save review: {e}")

with btn_cols[1]:
    if st.button("❌ Reject", type="secondary", use_container_width=True):
        try:
            write_review(facility_id, capability, "rejected", notes)
            st.warning(f"**{capability}** marked as **Rejected** and saved to Delta table.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save review: {e}")

with btn_cols[2]:
    if st.button("💾 Save Note", use_container_width=True):
        if not notes.strip():
            st.error("Add a note before saving.")
        else:
            try:
                write_review(facility_id, capability, "noted", notes)
                st.success("Note saved to Delta table.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save note: {e}")

st.divider()

# ── Review history ────────────────────────────────────────────────────────────
st.subheader("Review History for this Facility")

reviews = get_reviews(facility_id)
if reviews:
    df = pd.DataFrame(reviews)

    status_icons = {"verified": "✅", "rejected": "❌", "noted": "💾"}
    df["status"] = df["review_status"].apply(
        lambda s: f"{status_icons.get(s, '❓')} {s.capitalize()}"
    )

    display_cols = {
        "capability":    "Capability",
        "status":        "Status",
        "review_notes":  "Notes",
        "reviewed_at":   "Reviewed At",
        "reviewed_by":   "Reviewer",
    }
    display_df = df[[c for c in display_cols if c in df.columns]].rename(
        columns=display_cols
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.caption("No reviews yet for this facility.")

st.divider()
nav_cols = st.columns(3)
with nav_cols[0]:
    if st.button("← Back to Search"):
        st.switch_page("pages/1_facility_search.py")
with nav_cols[1]:
    if st.button("📊 Trust Report"):
        st.switch_page("pages/2_trust_report.py")
with nav_cols[2]:
    if st.button("🔬 Evidence Explorer"):
        st.switch_page("pages/3_evidence_explorer.py")
