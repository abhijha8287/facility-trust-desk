# Facility Trust Desk — Demo Script
### Target: Under 3 minutes

---

## The Problem (20s)

> "A healthcare NGO is about to fund a hospital that *claims* it has an ICU, NICU, and Trauma unit.
> How do they know it's real? They open a spreadsheet. That's the state of the art."

This app replaces the spreadsheet with AI-powered evidence assessment — backed by Databricks Unity Catalog.

---

## Step 1 — Search (20s)

**Open:** `http://localhost:8501/facility_search`

1. Type **"Aravind"** in the name box → click **Search Facilities**
2. Point to the results: *"Real data from the Virtue Foundation dataset on Databricks — 1,000+ facilities across India."*
3. Click the **Aravind Eye Hospital** row

**Say:** *"One click selects the facility and carries it through every page."*

---

## Step 2 — Generate Trust Assessment (50s) ← THE MONEY SHOT

**Opens automatically:** Trust Report page

1. Show the facility header: **Hyderabad · 650 beds · 38 doctors**
2. Click **"Generate Trust Assessment"**
3. Watch the spinner — *"7 LLM calls run in parallel. GPT-4o-mini reads every field: description, specialties, equipment, procedures."*
4. Results appear (~10s). Walk through two cards:
   - **✅ ICU — Strong Evidence (100%)** — *"22-bed Level II ICU with 11 ventilators. AI found concrete proof."*
   - **❌ Oncology — No Evidence (0%)** — *"Zero mentions of oncology anywhere in the record. Red flag for a funder."*

**Say:** *"First run calls the LLM. Every run after this is instant — scores are cached in a Delta table."*

---

## Step 3 — Evidence Explorer (30s)

**Click:** Evidence Explorer (nav button at bottom)

1. Expand the **ICU** section
2. Point to the source table: *"Every evidence snippet is traced back to its source field — description, equipment, specialties."*
3. Show the AI Reasoning block: *"Auditable. You can see exactly why the AI gave this score."*

**Say:** *"This is the traceability layer. Funders can verify every decision, not just trust a number."*

---

## Step 4 — Human Review Desk (30s)

**Click:** Human Review Desk (nav button)

1. Select **Maternity** from the dropdown — show **Partial Evidence (60%)**
2. Type in notes: *"Field visit confirmed delivery unit but no NICU adjacency"*
3. Click **✅ Verify**
4. Show the Review History table update: *"Written to Delta table. Auditable forever."*

**Say:** *"AI flags it. Human confirms it. Every decision is logged in Unity Catalog — full audit trail for grant accountability."*

---

## Close (10s)

> "Facility Trust Desk turns a 3-week manual verification process into a 10-second AI assessment —
> with full evidence traceability, human override, and an audit log that lives in Databricks forever."

**Show shareable URL:** `http://localhost:8501/trust_report?fid=b8a5401f-42f1-422a-8cd9-686a15b4cb76`

*"Every report is a shareable link. Send it to your donor in one click."*

---

## Timing Cheatsheet

| Segment | Time |
|---------|------|
| Problem statement | 0:00 – 0:20 |
| Facility Search | 0:20 – 0:40 |
| Trust Assessment (parallel LLM) | 0:40 – 1:30 |
| Evidence Explorer | 1:30 – 2:00 |
| Human Review + Delta write | 2:00 – 2:30 |
| Close + shareable URL | 2:30 – 2:40 |

**Total: ~2:40** ✅

---

## If Asked About the Stack

- **Data:** Databricks Unity Catalog · `virtue_foundation_dataset` (1,000+ real facilities)
- **LLM:** GPT-4o-mini · 7 parallel calls via `ThreadPoolExecutor`
- **Cache:** Delta table `facility_capability_scores` — LLM runs once, cached forever
- **Audit:** Delta table `facility_reviews` — every human decision persisted
- **Deploy:** Databricks Apps (`app.yaml`) · Streamlit frontend
