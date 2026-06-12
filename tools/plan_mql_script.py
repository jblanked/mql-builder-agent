"""Create a structured implementation plan for an MQL source file."""

from tools.tool import Parameters, Property, Tool


def plan_mql_script(request: str, mql_version: str, script_type: str, context_notes: str = "") -> dict:
    """
    Build a structured plan guiding the LLM when it writes the MQL source.

    Returns a dict the LLM can read to understand exactly what handlers,
    inputs, includes, and logic the generated file needs.
    """
    version = mql_version.upper().strip()
    script = script_type.lower().strip()

    ext = ".mq5" if version == "MQL5" else ".mq4"

    # Handlers per script type
    handlers: list[dict] = []
    if script == "indicator":
        handlers = [
            {"name": "OnInit", "purpose": "Set up indicator buffers, set ArraySetAsSeries, bind buffers, set short name."},
            {"name": "OnCalculate", "purpose": "Main calculation loop. Compute indicator values for each bar from start to rates_total."},
            {"name": "OnDeinit", "purpose": "Release indicator handles, cleanup."},
        ]
    elif script == "script":
        handlers = [
            {"name": "OnStart", "purpose": "Single execution entry point. Perform the one-shot task and return."},
        ]
    else:  # expert_advisor
        handlers = [
            {"name": "OnInit", "purpose": "Validate inputs, create indicator handles, set trade properties (magic, slippage, filling)."},
            {"name": "OnTick", "purpose": "Main trading logic: check new bar, read indicator values, evaluate signals, manage positions."},
            {"name": "OnDeinit", "purpose": "Release indicator handles, log shutdown reason."},
            {"name": "OnTimer", "purpose": "(Optional) Periodic tasks like status logging or heartbeat checks.", "optional": True},
            {"name": "OnChartEvent", "purpose": "(Optional) Handle button clicks or keyboard shortcuts.", "optional": True},
        ]

    # Required includes
    includes: list[str] = []
    if version == "MQL5":
        if script in ("expert_advisor", "script"):
            includes = ["Trade/Trade.mqh"]
            if script == "expert_advisor":
                includes.extend(["Trade/PositionInfo.mqh", "Trade/OrderInfo.mqh"])

    # Common inputs
    inputs: list[dict] = []
    if script == "expert_advisor":
        inputs = [
            {"name": "lot_size", "type": "double", "default": "0.1", "description": "Fixed Lot Size"},
            {"name": "magic_number", "type": "int", "default": "123456", "description": "Magic Number"},
            {"name": "slippage", "type": "int", "default": "30", "description": "Slippage (points)"},
        ]
    elif script == "script":
        inputs = [
            {"name": "lot_size", "type": "double", "default": "0.1", "description": "Lot Size"},
        ]
    elif script == "indicator":
        inputs = [
            {"name": "ma_period", "type": "int", "default": "14", "description": "Period"},
        ]

    # Version-specific guidance
    guidance: list[str] = []
    if version == "MQL5":
        guidance = [
            "Use CTrade class for all trade operations (Buy, Sell, PositionClose, PositionModify).",
            "Use CPositionInfo / COrderInfo for position/order iteration.",
            "Use indicator handles (iMA, iRSI, etc.) with CopyBuffer to retrieve data.",
            "Always call ArraySetAsSeries() on time-series arrays.",
            "Release indicator handles in OnDeinit with IndicatorRelease().",
            "Use SymbolInfoDouble/Integer for market properties.",
        ]
    else:
        guidance = [
            "Use OrderSend/OrderClose/OrderModify for all trade operations.",
            "Use OrderSelect with MODE_TRADES / MODE_HISTORY for iteration.",
            "Use built-in i-functions directly (iMA, iRSI, etc.) in expressions.",
            "Call ArraySetAsSeries() to ensure correct bar ordering.",
            "Use MarketInfo() for market properties.",
            "OrderTotal() / OrdersTotal() for counting.",
        ]

    plan = {
        "target_extension": ext,
        "mql_version": version,
        "script_type": script,
        "handlers": handlers,
        "required_includes": includes,
        "suggested_inputs": inputs,
        "version_guidance": guidance,
        "general_rules": [
            "Always use #property strict.",
            "Validate all input parameters in OnInit / OnStart.",
            "Use Print/PrintFormat for logging, not Comment().",
            "Check IsStopped() before long loops.",
            "Zero-divide protection on all calculations.",
            "NormalizeDouble() on all price values.",
            "Check trading permissions before any trade operation.",
        ],
        "context_notes": context_notes,
        "request_summary": request,
    }

    return plan


TOOL_PLAN_MQL_SCRIPT = Tool(
    name="plan_mql_script",
    description="Create a detailed implementation plan for an MQL source file including handlers, includes, inputs, and version-specific guidance.",
    parameters=Parameters(
        properties=[
            Property(name="request", type="string", description="The user's full request.", required=True),
            Property(name="mql_version", type="string", description="Detected MQL version: 'MQL4' or 'MQL5'.", required=True),
            Property(name="script_type", type="string", description="Detected script type: 'expert_advisor', 'indicator', or 'script'.", required=True),
            Property(name="context_notes", type="string", description="Relevant context notes from read_context.", required=False),
        ]
    ),
)
