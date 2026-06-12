"""Tool registry and execution dispatcher for the MQL builder agent."""

from tools.detect_mql_version import TOOL_DETECT_MQL_VERSION, detect_mql_version
from tools.plan_mql_script import TOOL_PLAN_MQL_SCRIPT, plan_mql_script
from tools.read_context import TOOL_READ_CONTEXT, read_context
from tools.write_mql_file import TOOL_WRITE_MQL_FILE, write_mql_file
from tools.build_output import TOOL_BUILD_OUTPUT, build_output

TOOLS = [
    TOOL_DETECT_MQL_VERSION,
    TOOL_PLAN_MQL_SCRIPT,
    TOOL_READ_CONTEXT,
    TOOL_WRITE_MQL_FILE,
    TOOL_BUILD_OUTPUT,
]

TOOL_MAP = {
    "detect_mql_version": detect_mql_version,
    "plan_mql_script": plan_mql_script,
    "read_context": read_context,
    "write_mql_file": write_mql_file,
    "build_output": build_output,
}


def execute_tool(name, args=None, **kwargs):
    """Execute a named tool with the given arguments."""
    payload = {}
    if args and isinstance(args, dict):
        payload.update(args)
    payload.update(kwargs)
    result = TOOL_MAP[name](**payload)
    return result
