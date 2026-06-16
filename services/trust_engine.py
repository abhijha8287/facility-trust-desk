import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
from openai import OpenAI

from utils.constants import CAPABILITIES
from utils.parsers import parse_array_field

SYSTEM_PROMPT = """You are a healthcare facility assessment analyst. Your job is to evaluate \
whether a facility can credibly perform a specific medical capability based ONLY on the \
text provided.

Rules:
- You MUST cite exact text snippets from the provided data as evidence.
- You MUST NOT invent or assume capabilities not mentioned in the data.
- If nothing in the data mentions the capability, use trust_level "No Evidence".
- Valid trust_level values (use exactly): "Strong Evidence" | "Partial Evidence" | \
"Weak Evidence" | "No Evidence"
- confidence_score: 0.0 (no confidence) to 1.0 (very confident)
- For each evidence snippet, note which field it came from in source_fields."""


def _build_user_prompt(facility: dict, capability: str) -> str:
    specialties = ", ".join(parse_array_field(facility.get("specialties"))) or "None listed"
    procedures = ", ".join(parse_array_field(facility.get("procedure"))) or "None listed"
    equipment = ", ".join(parse_array_field(facility.get("equipment"))) or "None listed"
    capabilities = ", ".join(parse_array_field(facility.get("capability"))) or "None listed"

    return f"""Evaluate whether this facility can perform: {capability}

FACILITY DATA:
Name: {facility.get("name", "")}
Description: {facility.get("description", "Not provided")}
Specialties: {specialties}
Procedures: {procedures}
Equipment: {equipment}
Listed Capabilities: {capabilities}
Doctors: {facility.get("numberDoctors", "Unknown")} | \
Capacity: {facility.get("capacity", "Unknown")} beds | \
Established: {facility.get("yearEstablished", "Unknown")}

Respond in JSON only, no other text:
{{
  "trust_level": "<one of: Strong Evidence | Partial Evidence | Weak Evidence | No Evidence>",
  "confidence_score": <0.0-1.0>,
  "evidence": ["exact quote from the facility data"],
  "missing_evidence": ["what additional information would confirm this"],
  "reasoning": "2-3 sentences citing specific evidence",
  "source_fields": {{"<exact quote>": "<field: description|specialties|procedure|equipment|capability>"}}
}}"""


def _safe_default(capability: str, reason: str = "LLM returned non-JSON response.") -> dict:
    return {
        "capability": capability,
        "trust_level": "No Evidence",
        "confidence_score": 0.0,
        "evidence": [],
        "missing_evidence": ["Full facility data review required."],
        "reasoning": reason,
        "source_fields": {},
    }


@st.cache_resource
def _get_llm_client() -> OpenAI:
    """OpenAI client — swap base_url for Databricks Foundation Models if needed."""
    api_key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")

    # Databricks Foundation Models switchover:
    # base_url = f"https://{os.environ.get('DATABRICKS_SERVER_HOSTNAME')}/serving-endpoints"
    # api_key = os.environ.get("DATABRICKS_TOKEN")
    # model = "databricks-meta-llama-3-3-70b-instruct"

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Add it to .env or Streamlit secrets."
        )
    return OpenAI(api_key=api_key)


def evaluate_capability(facility: dict, capability: str) -> dict:
    """Call the LLM to evaluate one capability. Returns a structured result dict."""
    client = _get_llm_client()
    prompt = _build_user_prompt(facility, capability)

    def _call(extra_prefix: str = "") -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": extra_prefix + prompt},
        ]
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content

    raw = ""
    try:
        raw = _call()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        try:
            raw = _call("Reply ONLY with valid JSON, no other text.\n\n")
            data = json.loads(raw)
        except Exception as e:
            return _safe_default(capability, f"Parse error: {e}")

    return {
        "capability": capability,
        "trust_level": data.get("trust_level", "No Evidence"),
        "confidence_score": float(data.get("confidence_score", 0.0)),
        "evidence": data.get("evidence", []),
        "missing_evidence": data.get("missing_evidence", []),
        "reasoning": data.get("reasoning", ""),
        "source_fields": data.get("source_fields", {}),
    }


def batch_evaluate(
    facility: dict,
    progress_placeholder=None,
) -> list[dict]:
    """Evaluate all 7 capabilities in parallel. Returns results in CAPABILITIES order."""
    results: dict[str, dict] = {}
    done = 0

    with ThreadPoolExecutor(max_workers=7) as executor:
        future_to_cap = {
            executor.submit(evaluate_capability, facility, cap): cap
            for cap in CAPABILITIES
        }
        for future in as_completed(future_to_cap):
            cap = future_to_cap[future]
            try:
                results[cap] = future.result()
            except Exception as e:
                results[cap] = _safe_default(cap, f"Evaluation failed: {e}")
            done += 1
            if progress_placeholder is not None:
                progress_placeholder.progress(
                    done / len(CAPABILITIES),
                    text=f"Evaluated {done}/{len(CAPABILITIES)} capabilities...",
                )

    return [results[cap] for cap in CAPABILITIES]
