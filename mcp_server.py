from mcp.server.fastmcp import FastMCP

from tools import dispatch

# Single compile-run workflow with local context
mcp = FastMCP("MqlAgent", instructions="You are an MQL coding agent for MetaTrader that creates and edits MQL4 and MQL5 scripts, expert advisors, and indicators. First determine whether the task targets MQL4 or MQL5 from the user's request, then read the most relevant context resources, plan the implementation, and write the code accordingly. The generated file must be compiled with MetaEditor as the final execution stage before producing the answer. Return only the structured output after build_output is called, and stop immediately when build_output completes.")


@mcp.tool(description="Detect whether the request targets MQL4 or MQL5 and infer the script type.")
def detect_mql_version(request: str):
    return dispatch.execute_tool("detect_mql_version", {"request": request})


@mcp.tool(description="Create a structured implementation plan for an MQL source file.")
def plan_mql_script(request: str, mql_version: str, script_type: str, context_notes: str = ""):
    return dispatch.execute_tool("plan_mql_script", {"request": request, "mql_version": mql_version, "script_type": script_type, "context_notes": context_notes})


@mcp.tool(description="Read one or more context files from the agent's context directory.")
def read_context(resources: str):
    return dispatch.execute_tool("read_context", {"resources": resources})


@mcp.tool(description="Write LLM-generated MQL source code to disk and compile it with MetaEditor.")
def write_mql_file(code: str, mql_version: str = "MQL5", output_path: str = "", metaeditor_path: str = "", compile: bool = True):
    return dispatch.execute_tool("write_mql_file", {"code": code, "mql_version": mql_version, "output_path": output_path, "metaeditor_path": metaeditor_path, "compile": compile})


@mcp.tool(description="Package the final compiled result into the structured output model. Always call this last.")
def build_output(script_type: str, mql_version: str, file_path: str, compilation_log: str, errors: str = "", warnings: str = ""):
    return dispatch.execute_tool("build_output", {"script_type": script_type, "mql_version": mql_version, "file_path": file_path, "compilation_log": compilation_log, "errors": errors, "warnings": warnings})


@mcp.resource("context://voice")
def voice():
    """Read the voice context file."""
    with open("context/voice.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://trade")
def trade():
    """Read the trade context file."""
    with open("context/trade.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://risk-management")
def risk_management():
    """Read the risk management context file."""
    with open("context/risk-management.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://object")
def object_ctx():
    """Read the object context file."""
    with open("context/object.md", "r", encoding="utf-8") as f:
        return f.read()
    
@mcp.resource("context://platform")
def platform():
    """Read the platform context file."""
    with open("context/platform.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://indicator")
def indicator():
    """Read the indicator context file."""
    with open("context/indicator.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://expert-advisor")
def expert_advisor():
    """Read the expert advisor context file."""
    with open("context/expert-advisor.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://script")
def script():
    """Read the script context file."""
    with open("context/script.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://chart")
def chart():
    """Read the chart context file."""
    with open("context/chart.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://terminal")
def terminal():
    """Read the terminal context file."""
    with open("context/terminal.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://strategies")
def strategies():
    """Read the strategies context file."""
    with open("context/strategies.md", "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("context://style")
def style():
    """Read the style context file."""
    with open("context/style.md", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run(transport="stdio")
