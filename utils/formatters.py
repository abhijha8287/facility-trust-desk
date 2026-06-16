from utils.constants import TRUST_COLORS, TRUST_ICONS


def trust_badge(trust_level: str) -> str:
    """Return an HTML badge for a trust level."""
    color = TRUST_COLORS.get(trust_level, "#6c757d")
    icon = TRUST_ICONS.get(trust_level, "❓")
    return (
        f'<span style="background-color:{color};color:white;'
        f'padding:3px 10px;border-radius:12px;font-size:0.85em;font-weight:600;">'
        f"{icon} {trust_level}</span>"
    )


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"
