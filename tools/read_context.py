from pathlib import Path

from tools.tool import Parameters, Property, Tool


def read_context(resources: str):
    """Read context files by name from the context directory."""
    base = Path(__file__).resolve().parent.parent / "context"
    names = [item.strip() for item in (resources or "").split(",") if item.strip()]
    parts = []
    for name in names:
        # Try exact name first, then append .md
        path = base / name
        if not path.exists():
            path = base / f"{name}.md"
        if path.exists():
            parts.append(f"## {name}\n{path.read_text(encoding='utf-8')}\n")
        else:
            parts.append(f"## {name}\n[Missing context file: {name}]\n")
    return "\n".join(parts).strip()


TOOL_READ_CONTEXT = Tool(
    name="read_context",
    description="Read one or more context files from the agent's context directory.",
    parameters=Parameters(
        properties=[
            Property(name="resources", type="string", description="Comma-separated context file names.", required=True),
        ]
    ),
)
