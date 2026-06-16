# 🏥 Facility Trust Desk

> **Databricks Apps & Agents for Good Hackathon 2026**
> Evidence-backed AI trust assessments for healthcare facilities — so NGOs and health planners fund what actually exists.

---

## The Problem

A healthcare NGO is about to allocate funds to a hospital that *claims* it has an ICU, NICU, and Trauma unit. How do they verify it? They open a spreadsheet and manually cross-reference documents — a process that takes weeks and still misses things.

**Facility Trust Desk replaces that with a 10-second AI assessment**, backed by direct evidence from the facility's own records, persisted in an auditable Delta table, and reviewable by a human analyst before any decision is made.

---

## Live Demo

**Try it now:** [facility-trust-desk-by-abhishek.streamlit.app](https://facility-trust-desk-by-abhishek.streamlit.app/)

**Shareable report URL example:**
```
https://facility-trust-desk-by-abhishek.streamlit.app/trust_report?fid=b8a5401f-42f1-422a-8cd9-686a15b4cb76
```
Every trust report is a permanent, shareable link — paste it in a grant application or donor email.

---

## Features

### 4 Pages

| Page | What it does |
|------|-------------|
| 🔍 **Facility Search** | Search 1,000+ real facilities by name, city, or state from the Virtue Foundation dataset |
| 📊 **Trust Report** | AI evaluates 7 critical capabilities in parallel (~10s). Results cached in Delta — instant on return visits |
| 🔬 **Evidence Explorer** | See exactly which source field (description, equipment, specialties…) each AI conclusion came from |
| 👤 **Human Review Desk** | Verify, reject, or annotate any AI assessment. Every decision written to an auditable Delta table |

### 7 Capabilities Evaluated

`ICU` · `NICU` · `Emergency Care` · `Trauma Care` · `Maternity` · `Oncology` · `Dialysis`

### Trust Levels

| Level | Meaning |
|-------|---------|
| ✅ **Strong Evidence** | Multiple independent signals confirm the capability |
| ⚠️ **Partial Evidence** | Some signals present but gaps remain |
| 🔶 **Weak Evidence** | One or two indirect mentions only |
| ❌ **No Evidence** | Dataset contains nothing supporting the claim |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  Search → Trust Report → Evidence Explorer → Human Review   │
└────────────────────────┬────────────────────────────────────┘
                         │
           ┌─────────────▼──────────────┐
           │      services/db.py        │  Databricks SQL Connector
           │  - search_facilities()     │  @st.cache_resource (singleton conn)
           │  - get_cached_scores()     │  @st.cache_data (dropdown data, 1h TTL)
           │  - write_capability_score()│  DELETE + INSERT upsert
           │  - write_review()          │  Append-only audit log
           └─────────────┬──────────────┘
                         │
           ┌─────────────▼──────────────┐
           │   services/trust_engine.py │  OpenAI GPT-4o-mini
           │  - batch_evaluate()        │  ThreadPoolExecutor(max_workers=7)
           │  - evaluate_capability()   │  Parallel — 7 calls in ~10s
           └────────────────────────────┘
                         │
        ┌────────────────▼────────────────────────────────┐
        │                Databricks Unity Catalog          │
        │                                                  │
        │  READ (source data):                             │
        │  databricks_virtue_foundation_dataset_dais_2026  │
        │    .virtue_foundation_dataset.facilities         │
        │                                                  │
        │  WRITE (app creates these):                      │
        │  workspace.default.facility_capability_scores    │
        │  workspace.default.facility_reviews              │
        └──────────────────────────────────────────────────┘
```

### Key Design Decisions

- **Write-through Delta cache** — LLM runs once per facility per capability. On a cache hit the Trust Report page loads instantly with zero LLM cost.
- **Parallel evaluation** — `ThreadPoolExecutor(max_workers=7)` runs all 7 capability checks simultaneously, cutting wall time from ~40s to ~10s.
- **Parameterized queries** — all user input goes through `?` placeholders, never string-interpolated. No SQL injection surface.
- **`st.secrets` → `os.environ` fallback** — same code works locally (reads `.env`) and on Streamlit Cloud / Databricks Apps (reads secrets UI).
- **Shareable `?fid=` URLs** — every page accepts a `?fid=<facility_id>` query parameter so reports can be linked directly without navigating through the search UI.

---

## Project Structure

```
facility-trust-desk/
├── app.py                          # Entry point — page config, sidebar, home
├── pages/
│   ├── 1_facility_search.py        # Search + row selection
│   ├── 2_trust_report.py           # Parallel LLM evaluation + Delta cache
│   ├── 3_evidence_explorer.py      # Source field traceability
│   └── 4_human_review.py           # Human override + audit log
├── services/
│   ├── db.py                       # All Databricks SQL operations
│   └── trust_engine.py             # OpenAI LLM calls, batch_evaluate()
├── utils/
│   ├── constants.py                # CAPABILITIES, TRUST_COLORS, SOURCE_TABLE
│   ├── formatters.py               # trust_badge(), confidence_label()
│   └── parsers.py                  # parse_array_field() for JSON/list fields
├── database/
│   ├── init_tables.sql             # Authoritative Delta table schemas
│   └── queries.sql                 # Reference queries with parameterization notes
├── .env.example                    # Template — copy to .env for local dev
├── .streamlit/secrets.toml.example # Template for Streamlit Cloud secrets
├── app.yaml                        # Databricks Apps deployment config
├── requirements.txt

```

---

## Local Setup

### Prerequisites
- Python 3.10+
- Access to the Databricks workspace with the Virtue Foundation dataset
- OpenAI API key

### Install

```bash
git clone https://github.com/abhijha8287/facility-trust-desk.git
cd facility-trust-desk
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` with your real values:

```env
DATABRICKS_SERVER_HOSTNAME=dbc-xxxxxxxx-xxxx.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/xxxxxxxxxxxxxxxx
DATABRICKS_TOKEN=dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TARGET_CATALOG=workspace
TARGET_SCHEMA=default
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

### Run

```bash
streamlit run app.py
```

App opens at `http://localhost:8501`.

---

## Deploy to Streamlit Community Cloud

1. Push to GitHub (already done)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Set:
   - Repository: `abhijha8287/facility-trust-desk`
   - Branch: `master`
   - Main file: `app.py`
4. Click **Advanced settings → Secrets** and paste:

```toml
DATABRICKS_SERVER_HOSTNAME = "dbc-xxxxxxxx-xxxx.cloud.databricks.com"
DATABRICKS_HTTP_PATH       = "/sql/1.0/warehouses/xxxxxxxxxxxxxxxx"
DATABRICKS_TOKEN           = "dapixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TARGET_CATALOG             = "workspace"
TARGET_SCHEMA              = "default"
OPENAI_API_KEY             = "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
OPENAI_MODEL               = "gpt-4o-mini"
```

5. Click **Deploy** — first boot takes ~60s.

---

## Deploy to Databricks Apps

```bash
databricks apps deploy facility-trust-desk --source-code-path .
```

On Databricks Apps the workspace credentials are injected automatically — no `DATABRICKS_TOKEN` needed in secrets.

---

## Delta Table Schemas

### `facility_capability_scores`
Stores LLM assessment results. Acts as a write-through cache.

| Column | Type | Description |
|--------|------|-------------|
| `facility_id` | STRING | Facility unique ID from source table |
| `facility_name` | STRING | Denormalized for quick display |
| `capability` | STRING | One of the 7 evaluated capabilities |
| `trust_level` | STRING | Strong Evidence / Partial / Weak / No Evidence |
| `confidence_score` | DOUBLE | 0.0 – 1.0 |
| `evidence_json` | STRING | JSON array of supporting text snippets |
| `missing_evidence_json` | STRING | JSON array of what would strengthen the assessment |
| `reasoning` | STRING | Full LLM reasoning paragraph |
| `last_updated` | TIMESTAMP | UTC timestamp of last evaluation |

### `facility_reviews`
Append-only human decision audit log.

| Column | Type | Description |
|--------|------|-------------|
| `facility_id` | STRING | Facility unique ID |
| `capability` | STRING | Capability being reviewed |
| `review_status` | STRING | `verified` / `rejected` / `noted` |
| `review_notes` | STRING | Free-text analyst notes |
| `reviewed_at` | TIMESTAMP | UTC timestamp |
| `reviewed_by` | STRING | Reviewer identifier (default: `analyst`) |

---

## Data Source

**Virtue Foundation Dataset** — Databricks Unity Catalog
```
databricks_virtue_foundation_dataset_dais_2026
  .virtue_foundation_dataset
  .facilities
```
1,000+ real healthcare facilities across India with structured fields: `description`, `specialties`, `procedure`, `equipment`, `capability`, `capacity`, `numberDoctors`, and address fields.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit ≥ 1.35 |
| AI / LLM | OpenAI GPT-4o-mini (parallel via `ThreadPoolExecutor`) |
| Data warehouse | Databricks SQL Warehouse |
| Storage | Delta Lake (Unity Catalog) |
| Deployment | Streamlit Community Cloud · Databricks Apps |
| Language | Python 3.10+ |

---

## Security Notes

- `.env` is in `.gitignore` — never committed
- All user input uses parameterized `?` placeholders — no SQL injection
- Catalog/schema names come from env vars (admin-controlled), not user input
- Source table is read-only; app writes only to its own two tables

---

*Built for the Databricks Apps & Agents for Good Hackathon 2026.*
