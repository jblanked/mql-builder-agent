"""Tool that writes LLM-generated MQL source code to disk and optionally compiles it."""

from pathlib import Path
import os
import subprocess
import re

from tools.tool import Parameters, Property, Tool

# Default MetaEditor paths; override via argument.
METAEDITOR_MQL5 = r"C:\Program Files\MetaTrader 5\metaeditor64.exe"
METAEDITOR_MQL4 = r"C:\Program Files\MetaTrader 4\metaeditor.exe"


def _compile_with_metaeditor(source_path: str, metaeditor_path: str = "") -> str:
    """Compile an MQL file with MetaEditor and return the log output."""
    ext = os.path.splitext(source_path)[1].lower()

    if not metaeditor_path:
        metaeditor_path = METAEDITOR_MQL5 if ext == ".mq5" else METAEDITOR_MQL4

    if not os.path.isfile(metaeditor_path):
        return f"MetaEditor not found at: {metaeditor_path}"

    log_path = source_path.replace(ext, ".log")
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except PermissionError:
            pass

    try:
        subprocess.run(
            [metaeditor_path, f"/compile:{source_path}", "/log"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return "Compilation timed out after 60 seconds."
    except FileNotFoundError:
        return f"MetaEditor executable not found: {metaeditor_path}"

    if not os.path.exists(log_path):
        return "No log file generated."

    with open(log_path, "r", encoding="utf-16") as f:
        return f.read()


def _parse_compilation_log(log: str) -> tuple[list[str], list[str]]:
    """Extract errors and warnings from a MetaEditor compilation log."""
    errors: list[str] = []
    warnings: list[str] = []
    for line in log.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        # Skip result summary lines
        if "result:" in lower and "error" in lower and "warning" in lower:
            continue
        if "error" in lower:
            errors.append(stripped)
        elif "warning" in lower:
            warnings.append(stripped)
    return errors, warnings


def write_mql_file(
    code: str,
    mql_version: str = "MQL5",
    output_path: str = "",
    metaeditor_path: str = "",
    compile: bool = True,
) -> dict:
    """
    Write LLM-generated MQL source code to disk. Optionally compile it.

    Args:
        code: The complete MQL4/MQL5 source code to write.
        mql_version: 'MQL4' or 'MQL5' — determines file extension.
        output_path: Optional absolute or relative path for the output file.
                     If empty, auto-generates a filename in the generated/ folder.
        metaeditor_path: Optional path to metaeditor64.exe or metaeditor.exe.
                         Defaults to standard MetaTrader install paths on Windows.
        compile: If True, attempts to compile the file using MetaEditor.

    Returns:
        dict with file_path, compilation_log, errors, warnings.
    """
    version = mql_version.upper().strip()
    ext = ".mq5" if version == "MQL5" else ".mq4"
    out_dir = Path(__file__).resolve().parent.parent / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    if output_path:
        source_path = str(
            (Path(output_path) if os.path.isabs(output_path) else out_dir / output_path).resolve()
        )
    else:
        # Auto-name from #property or fallback
        base_name = "mql_agent_generated"
        name_match = re.search(r'property\s+version\s+"([^"]+)"', code)
        if not name_match:
            name_match = re.search(r"//\s*Name:\s*(\S+)", code)
        if name_match:
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name_match.group(1))
            base_name = safe_name
        source_path = str((out_dir / f"{base_name}{ext}").resolve())

    # Ensure the correct file extension
    if not source_path.lower().endswith(ext):
        source_path = source_path[: source_path.rfind(".")] + ext if "." in source_path else source_path + ext

    Path(source_path).write_text(code, encoding="utf-8")

    compilation_log = ""
    if compile:
        compilation_log = _compile_with_metaeditor(source_path, metaeditor_path)
    else:
        compilation_log = "Compilation skipped (compile=False)."

    errors_list, warnings_list = _parse_compilation_log(compilation_log)

    return {
        "file_path": source_path,
        "compilation_log": compilation_log,
        "errors": errors_list,
        "warnings": warnings_list,
    }


TOOL_WRITE_MQL_FILE = Tool(
    name="write_mql_file",
    description="Write LLM-generated MQL source code to disk. Compiles with MetaEditor by default and returns errors/warnings.",
    parameters=Parameters(
        properties=[
            Property(name="code", type="string", description="Complete MQL4/MQL5 source code to write.", required=True),
            Property(name="mql_version", type="string", description="Target MQL version: 'MQL4' or 'MQL5'.", required=True),
            Property(name="output_path", type="string", description="Optional output file path.", required=False),
            Property(name="metaeditor_path", type="string", description="Optional path to metaeditor64.exe or metaeditor.exe.", required=False),
            Property(name="compile", type="boolean", description="Whether to compile with MetaEditor. Default true.", required=False),
        ]
    ),
)
