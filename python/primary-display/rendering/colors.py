"""MGB Dash 2026 — Color palette constants."""

# Freshness colors (R, G, B, A) — 0.0 to 1.0
FRESH_GREEN  = (0.20, 0.85, 0.30, 1.0)   # < 2 s
AGING_YELLOW = (0.95, 0.85, 0.15, 1.0)   # 2–5 s
STALE_ORANGE = (0.95, 0.55, 0.10, 1.0)   # 5–10 s
DEAD_RED     = (0.90, 0.15, 0.15, 1.0)   # 10–30 s
NEVER_GRAY   = (0.30, 0.30, 0.30, 1.0)   # > 30 s or never

# Background
BG_BLACK = (0.0, 0.0, 0.0, 1.0)

# Text
TEXT_WHITE = (1.0, 1.0, 1.0, 1.0)
TEXT_DIM   = (0.55, 0.55, 0.55, 1.0)
TEXT_LABEL = (0.70, 0.70, 0.75, 1.0)

# UI accents
GROUP_HEADER = (0.40, 0.50, 0.70, 1.0)

# Arc gauge fills
ARC_SPEED          = (0.80, 0.41, 0.20, 1.0)   # orange/copper
ARC_AMPS_DISCHARGE = (0.70, 0.12, 0.12, 1.0)   # dark red (discharging)
ARC_AMPS_REGEN     = (0.20, 0.75, 0.30, 1.0)   # green (regenerating)
ARC_RANGE          = (0.90, 0.55, 0.15, 1.0)   # orange (current estimate)
ARC_RANGE_OPTIMIST = (0.35, 0.90, 0.50, 1.0)   # bright green (best case)
ARC_RANGE_PESSIMIST= (0.85, 0.30, 0.30, 1.0)   # light red (worst case)
ARC_TRACK          = (0.15, 0.15, 0.15, 1.0)   # dark gray background

# Alert severities
ALERT_RED    = (0.90, 0.15, 0.15, 1.0)
ALERT_YELLOW = (0.95, 0.85, 0.15, 1.0)
ALERT_CYAN   = (0.0,  0.85, 0.90, 1.0)


def freshness_color(age_seconds: float) -> tuple:
    """Return RGBA tuple for the given signal age."""
    if age_seconds < 2.0:
        return FRESH_GREEN
    if age_seconds < 5.0:
        return AGING_YELLOW
    if age_seconds < 10.0:
        return STALE_ORANGE
    if age_seconds < 30.0:
        return DEAD_RED
    return NEVER_GRAY
