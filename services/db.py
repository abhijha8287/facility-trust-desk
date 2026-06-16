import json
import os
from datetime import datetime, timezone

import streamlit as st
from databricks import sql

from utils.constants import SOURCE_TABLE


def _cfg(key: str) -> str:
    """Read from Streamlit secrets first, then env vars."""
    try:
        return st.secrets[key]
    except Exception:
        val = os.environ.get(key, "")
        if not val:
            raise RuntimeError(
                f"Missing config: {key}. Set it in .env or Streamlit secrets."
            )
        return val


def _write_table(name: str) -> str:
    catalog = _cfg("TARGET_CATALOG")
    schema = _cfg("TARGET_SCHEMA")
    return f"`{catalog}`.`{schema}`.`{name}`"


@st.cache_resource
def get_connection():
    return sql.connect(
        server_hostname=_cfg("DATABRICKS_SERVER_HOSTNAME"),
        http_path=_cfg("DATABRICKS_HTTP_PATH"),
        access_token=_cfg("DATABRICKS_TOKEN"),
    )


def _run(query: str, params: list | None = None) -> list[dict]:
    """Execute a SELECT and return rows as dicts. Creates a new cursor each call."""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(query, params or [])
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _execute(query: str, params: list | None = None) -> None:
    """Execute a DML/DDL statement (INSERT, DELETE, CREATE)."""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(query, params or [])


# ---------------------------------------------------------------------------
# Table initialisation (called once at app startup)
# ---------------------------------------------------------------------------

def init_tables() -> None:
    reviews = _write_table("facility_reviews")
    scores = _write_table("facility_capability_scores")

    ddl_reviews = f"""
    CREATE TABLE IF NOT EXISTS {reviews} (
      facility_id    STRING NOT NULL,
      capability     STRING NOT NULL,
      review_status  STRING NOT NULL,
      review_notes   STRING,
      reviewed_at    TIMESTAMP NOT NULL,
      reviewed_by    STRING
    ) USING DELTA
    """

    ddl_scores = f"""
    CREATE TABLE IF NOT EXISTS {scores} (
      facility_id           STRING NOT NULL,
      facility_name         STRING,
      capability            STRING NOT NULL,
      trust_level           STRING NOT NULL,
      confidence_score      DOUBLE NOT NULL,
      evidence_json         STRING,
      missing_evidence_json STRING,
      reasoning             STRING,
      last_updated          TIMESTAMP NOT NULL
    ) USING DELTA
    """

    try:
        _execute(ddl_reviews)
        _execute(ddl_scores)
    except Exception as e:
        catalog = _cfg("TARGET_CATALOG")
        schema = _cfg("TARGET_SCHEMA")
        st.error(
            f"Cannot create tables in `{catalog}`.`{schema}`. "
            f"Ask your Databricks admin to run:\n\n"
            f"```sql\nGRANT CREATE TABLE ON SCHEMA {catalog}.{schema} TO '<your-user>';\n```\n\n"
            f"Error: {e}"
        )
        st.stop()


# ---------------------------------------------------------------------------
# Facility reads
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_distinct_cities() -> list[str]:
    rows = _run(
        f"SELECT DISTINCT address_city FROM {SOURCE_TABLE} "
        "WHERE address_city IS NOT NULL ORDER BY 1 LIMIT 200"
    )
    return [""] + [r["address_city"] for r in rows]


@st.cache_data(ttl=3600)
def get_distinct_states() -> list[str]:
    rows = _run(
        f"SELECT DISTINCT address_stateOrRegion FROM {SOURCE_TABLE} "
        "WHERE address_stateOrRegion IS NOT NULL ORDER BY 1"
    )
    return [""] + [r["address_stateOrRegion"] for r in rows]


def search_facilities(
    name_query: str = "",
    city_filter: str = "",
    state_filter: str = "",
) -> list[dict]:
    conditions = ["1=1"]
    params: list = []

    if name_query.strip():
        conditions.append("LOWER(name) LIKE ?")
        params.append(f"%{name_query.lower()}%")

    if city_filter:
        conditions.append("address_city = ?")
        params.append(city_filter)

    if state_filter:
        conditions.append("address_stateOrRegion = ?")
        params.append(state_filter)

    where = " AND ".join(conditions)
    sql_query = (
        f"SELECT unique_id, name, address_city, address_stateOrRegion, "
        f"numberDoctors, capacity "
        f"FROM {SOURCE_TABLE} WHERE {where} LIMIT 100"
    )
    return _run(sql_query, params)


def get_facility_detail(facility_id: str) -> dict | None:
    rows = _run(f"SELECT * FROM {SOURCE_TABLE} WHERE unique_id = ?", [facility_id])
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Trust score cache
# ---------------------------------------------------------------------------

def get_cached_scores(facility_id: str) -> list[dict]:
    table = _write_table("facility_capability_scores")
    rows = _run(
        f"SELECT * FROM {table} WHERE facility_id = ?",
        [facility_id],
    )
    for row in rows:
        for key in ("evidence_json", "missing_evidence_json"):
            if row.get(key):
                try:
                    row[key] = json.loads(row[key])
                except Exception:
                    row[key] = []
    return rows


def write_capability_score(
    facility_id: str,
    facility_name: str,
    capability: str,
    trust_level: str,
    confidence_score: float,
    evidence: list[str],
    missing_evidence: list[str],
    reasoning: str,
) -> None:
    table = _write_table("facility_capability_scores")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    _execute(
        f"DELETE FROM {table} WHERE facility_id = ? AND capability = ?",
        [facility_id, capability],
    )
    _execute(
        f"INSERT INTO {table} "
        "(facility_id, facility_name, capability, trust_level, confidence_score, "
        "evidence_json, missing_evidence_json, reasoning, last_updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            facility_id,
            facility_name,
            capability,
            trust_level,
            confidence_score,
            json.dumps(evidence),
            json.dumps(missing_evidence),
            reasoning,
            now,
        ],
    )


# ---------------------------------------------------------------------------
# Human reviews
# ---------------------------------------------------------------------------

def write_review(
    facility_id: str,
    capability: str,
    status: str,
    notes: str,
    reviewed_by: str = "analyst",
) -> None:
    table = _write_table("facility_reviews")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    _execute(
        f"INSERT INTO {table} "
        "(facility_id, capability, review_status, review_notes, reviewed_at, reviewed_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [facility_id, capability, status, notes or "", now, reviewed_by],
    )


def get_reviews(facility_id: str) -> list[dict]:
    table = _write_table("facility_reviews")
    return _run(
        f"SELECT * FROM {table} WHERE facility_id = ? ORDER BY reviewed_at DESC",
        [facility_id],
    )
