"""Package the final compiled MQL result into the structured output model."""

import re

from tools.tool import Parameters, Property, Tool


def _parse_log_issues(compilation_log: str) -> tuple[list[str], list[str]]:
    """Extract errors and warnings from a MetaEditor compilation log."""
    errors: list[str] = []
    warnings: list[str] = []
    if not compilation_log:
        return errors, warnings

    for line in compilation_log.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        # Skip summary lines
        if "result:" in lower and "error" in lower and "warning" in lower:
            continue
        if " : error " in lower or "error:" in lower or "\terror" in lower:
            errors.append(stripped)
        elif " : warning " in lower or "warning:" in lower or "\twarning" in lower:
            warnings.append(stripped)
        # Catch non-zero error counts
        elif re.search(r'\d+\s+errors?', lower) and '0 errors' not in lower:
            if stripped not in errors:
                errors.append(stripped)

    return errors, warnings


def build_output(
    script_type: str,
    mql_version: str,
    file_path: str,
    compilation_log: str,
    errors: list[str] | str | None = None,
    warnings: list[str] | str | None = None,
) -> dict:
    """
    Build the structured output for the MQL agent.

    Accepts errors/warnings as lists or strings. If compilation_log is
    provided and errors/warnings are empty, parses the log automatically.
    """
    # Normalize errors
    if errors is None:
        errors_normalized: list[str] = []
    elif isinstance(errors, str):
        errors_normalized = [errors] if errors.strip() else []
    elif isinstance(errors, list):
        errors_normalized = [str(e) for e in errors if str(e).strip()]
    else:
        errors_normalized = []

    # Normalize warnings
    if warnings is None:
        warnings_normalized: list[str] = []
    elif isinstance(warnings, str):
        warnings_normalized = [warnings] if warnings.strip() else []
    elif isinstance(warnings, list):
        warnings_normalized = [str(w) for w in warnings if str(w).strip()]
    else:
        warnings_normalized = []

    # Auto-parse from log
    if not errors_normalized and not warnings_normalized and compilation_log:
        errors_normalized, warnings_normalized = _parse_log_issues(compilation_log)

    # Determine status
    if errors_normalized:
        status = "compilation_failed"
    elif warnings_normalized:
        status = "compiled_with_warnings"
    elif compilation_log and "no log file" not in compilation_log.lower():
        status = "compiled_successfully"
    else:
        status = "unknown"

    return {
        "script_type": script_type,
        "mql_version": mql_version,
        "file_path": file_path,
        "compilation_log": compilation_log,
        "errors": errors_normalized,
        "warnings": warnings_normalized,
        "status": status,
    }


TOOL_BUILD_OUTPUT = Tool(
    name="build_output",
    description="Package the final compiled result into the structured output model. Always call this last.",
    parameters=Parameters(
        properties=[
            Property(name="script_type", type="string", description="Generated file type: expert_advisor, indicator, or script.", required=True),
            Property(name="mql_version", type="string", description="Detected MQL version: MQL4 or MQL5.", required=True),
            Property(name="file_path", type="string", description="Path to the generated .mq4 or .mq5 file.", required=True),
            Property(name="compilation_log", type="string", description="Full compilation log from MetaEditor.", required=True),
            Property(name="errors", type="string", description="Compilation errors (comma-separated or JSON array).", required=False),
            Property(name="warnings", type="string", description="Compilation warnings (comma-separated or JSON array).", required=False),
        ]
    ),
)
