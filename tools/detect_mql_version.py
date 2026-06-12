"""Detect whether a user request targets MQL4 or MQL5 and what script type."""

from tools.tool import Parameters, Property, Tool


# Keyword scoring tables

MQL4_KEYWORDS = [
    "mql4", "mt4", ".mq4", "metatrader 4", "ordersend", "orderclose",
    "ordermodify", "orderselect", "ordertotal", "marketinfo",
    "mode_trades", "mode_history",
]
MQL5_KEYWORDS = [
    "mql5", "mt5", ".mq5", "metatrader 5", "ctrade", "cpositioninfo",
    "corderinfo", "positionselect", "positiontotal", "historyselect",
    "symbolinfodouble", "symbolinfointeger", "copybuffer",
]

EA_KEYWORDS = [
    "expert advisor", "ea", "oninit", "ontick", "ondeinit",
    "expert", "automated trading", "autotrade", "bot",
]
INDICATOR_KEYWORDS = [
    "indicator", "custom indicator", "icustom", "oncalculate",
    "indicator_chart_window", "indicator_separate_window",
    "indicator_buffers", "draw_line", "draw_histogram",
    "plotindex", "setindexbuffer",
]
SCRIPT_KEYWORDS = [
    "script", "onstart", "one-shot", "one shot",
    "run once", "execute once",
]


def detect_mql_version(request: str) -> dict:
    """Analyze the user request to determine MQL4 vs MQL5 and script type."""
    text = (request or "").lower()

    # Score version
    mql4_score = sum(1 for kw in MQL4_KEYWORDS if kw in text)
    mql5_score = sum(1 for kw in MQL5_KEYWORDS if kw in text)

    # Score script type
    ea_score = sum(1 for kw in EA_KEYWORDS if kw in text)
    indicator_score = sum(1 for kw in INDICATOR_KEYWORDS if kw in text)
    script_score = sum(1 for kw in SCRIPT_KEYWORDS if kw in text)

    rationale_parts: list[str] = []
    version: str
    confidence: float

    if mql4_score > mql5_score:
        version = "MQL4"
        confidence = min(0.97, 0.5 + mql4_score * 0.15)
        rationale_parts.append(f"Found {mql4_score} MQL4 signals vs {mql5_score} MQL5 signals.")
    elif mql5_score > mql4_score:
        version = "MQL5"
        confidence = min(0.97, 0.5 + mql5_score * 0.15)
        rationale_parts.append(f"Found {mql5_score} MQL5 signals vs {mql4_score} MQL4 signals.")
    elif mql4_score == 0 and mql5_score == 0:
        version = "MQL5"  # Default to MQL5 (newer)
        confidence = 0.55
        rationale_parts.append("No version keywords; defaulting to MQL5.")
    else:
        version = "MQL5"
        confidence = 0.65
        rationale_parts.append("Ambiguous version signals; defaulting to MQL5.")

    # Determine script type
    script_type: str
    if indicator_score > ea_score and indicator_score > script_score:
        script_type = "indicator"
        rationale_parts.append("Indicator-specific terms dominate.")
    elif script_score > ea_score and script_score > indicator_score:
        script_type = "script"
        rationale_parts.append("Script-specific terms dominate.")
    elif ea_score > 0 or (ea_score == 0 and indicator_score == 0 and script_score == 0):
        script_type = "expert_advisor"
        if ea_score > 0:
            rationale_parts.append("Expert Advisor terminology detected.")
        else:
            rationale_parts.append("No script type specified; defaulting to Expert Advisor.")
    else:
        script_type = "expert_advisor"
        rationale_parts.append("Defaulting to Expert Advisor.")

    return {
        "mql_version": version,
        "script_type": script_type,
        "confidence": round(confidence, 2),
        "rationale": " ".join(rationale_parts),
    }


TOOL_DETECT_MQL_VERSION = Tool(
    name="detect_mql_version",
    description="Detect whether a user request targets MQL4 or MQL5 and which script type (EA, indicator, or script) is needed.",
    parameters=Parameters(
        properties=[
            Property(name="request", type="string", description="The user's full request text.", required=True),
        ]
    ),
)
