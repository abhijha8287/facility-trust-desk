import json
import re


def parse_array_field(value) -> list[str]:
    """Parse a DB column that may be a JSON array, single-quoted array, NULL, or empty string."""
    if value is None:
        return []
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return []

    # Try standard JSON first
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item]
        return [str(parsed).strip()]
    except json.JSONDecodeError:
        pass

    # Handle single-quoted Python-style lists: ['ICU', 'Emergency']
    try:
        normalized = value.replace("'", '"')
        parsed = json.loads(normalized)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fall back: strip brackets and split on commas
    cleaned = re.sub(r"^[\[\(]|[\]\)]$", "", value)
    parts = [p.strip().strip("'\"") for p in cleaned.split(",")]
    return [p for p in parts if p]
