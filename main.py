import asyncio
import json
import os
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from llm_providers import PROVIDER, post_chat_completion

AGENT_NAME = "MQL Builder Agent"
AGENT_DESCRIPTION = "Creates and edits MQL4/MQL5 scripts, expert advisors, and indicators for MetaTrader."
PROMPT = "You are an MQL coding agent for MetaTrader that creates and edits MQL4 and MQL5 scripts, expert advisors, and indicators. First determine whether the task targets MQL4 or MQL5 from the user's request, then read the most relevant context resources, plan the implementation, and write the code accordingly. The generated file must be compiled with MetaEditor as the final execution stage before producing the answer. Return only the structured output after build_output is called, and stop immediately when build_output completes."
MAX_TOOL_ITERATIONS = 50
CONTEXT_RESOURCE_URIS = [
    "context://voice",
    "context://trade",
    "context://risk-management",
    "context://object",
    "context://indicator",
    "context://expert-advisor",
    "context://script",
    "context://chart",
    "context://terminal",
    "context://strategies",
    "context://style",
]

MQL_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "utf-16",
    "utf-16-le",
    "utf-16-be",
    "cp1252",
    "latin-1",
)


def _read_mql_file(file_path: str) -> tuple[str, str]:
    """Read an MQL file with encoding fallback. Returns (content, file_extension_lower)."""
    path = os.path.expanduser(file_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()

    with open(path, "rb") as fh:
        raw = fh.read()

    for encoding in MQL_ENCODINGS:
        try:
            return raw.decode(encoding), ext
        except (UnicodeDecodeError, LookupError):
            continue

    # Last resort
    return raw.decode("utf-8", errors="replace"), ext


def _sanitize_conversation(conversation: list[dict]) -> list[dict]:
    """Deep-copy conversation and ensure content is always a string."""
    sanitized: list[dict] = []
    for message in conversation:
        item = dict(message)
        content = item.get("content")
        # Content must be string or null
        if isinstance(content, (dict, list)):
            item["content"] = json.dumps(content, ensure_ascii=False)
        elif content is None:
            item["content"] = ""
        if "tool_calls" in item and item["tool_calls"] is None:
            del item["tool_calls"]
        sanitized.append(item)
    return sanitized


async def _run_agent_async(topic: str, file_path: str = ""):
    """Run the MQL agent loop with tool orchestration.

    Args:
        topic: The user's request describing what to create or edit.
        file_path: Optional path to an existing .mq4/.mq5 file to edit.
                   When provided, the file content is loaded and injected
                   into the conversation so the agent works on that file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(base_dir, "mcp_server.py")],
        cwd=base_dir,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("\033[90m[Agent] MCP session initialized\033[0m")
            tool_list = await session.list_tools()
            tools = []
            for tool in tool_list.tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                    },
                })

            tools_count = len(tools)
            print(f"\033[90m[Agent] Discovered {tools_count} tools\033[0m")

            context_parts = []
            for uri in CONTEXT_RESOURCE_URIS:
                print(f"\033[90m[Agent] Loading context: {uri}\033[0m")
                resource = await session.read_resource(uri)
                text = ""
                if hasattr(resource, "contents") and resource.contents:
                    for block in resource.contents:
                        if hasattr(block, "text"):
                            text += block.text
                context_parts.append(f"### {uri}\n{text}")

            conversation = [
                {"role": "system", "content": PROMPT},
                {"role": "system", "content": "\n\n".join(context_parts)},
            ]

            if file_path:
                resolved = os.path.expanduser(file_path)
                try:
                    file_content, ext = _read_mql_file(resolved)
                    mql_ver = "MQL5" if ext == ".mq5" else "MQL4"
                    print(f"\033[90m[Agent] Editing file: {os.path.abspath(resolved)} ({mql_ver}, {len(file_content)} chars)\033[0m")
                    conversation.append({
                        "role": "user",
                        "content": (
                            f"I need you to EDIT the existing {mql_ver} file at:\n"
                            f"{os.path.abspath(resolved)}\n\n"
                            f"Here is the current content of the file:\n"
                            f"```{ext[1:]}\n{file_content}\n```\n\n"
                            f"My request: {topic}\n\n"
                            f"IMPORTANT: You are EDITING this existing file, not creating a new one. "
                            f"Use write_mql_file with output_path set to the same path to overwrite it "
                            f"after applying the changes. Read relevant context files based on what the "
                            f"file contains (EA, indicator, or script) and what needs to change."
                        ),
                    })
                except FileNotFoundError as exc:
                    return json.dumps({"status": "error", "message": str(exc)})
            else:
                conversation.append({"role": "user", "content": topic})

            for _ in range(MAX_TOOL_ITERATIONS):
                payload = {
                    "model": PROVIDER.model,
                    "messages": _sanitize_conversation(conversation),
                    "temperature": 0.2,
                    "tools": tools,
                    "tool_choice": "auto",
                }
                response = post_chat_completion(payload)
                message = response["choices"][0]["message"]
                tool_calls = message.get("tool_calls") or []
                if tool_calls:
                    assistant_message = {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": tool_calls,
                    }
                    if any(call.get("function", {}).get("name") == "build_output" for call in tool_calls):
                        print("\033[90m[Agent] build_output triggered -- finalizing\033[0m")
                        conversation.append(assistant_message)
                        for call in tool_calls:
                            function = call["function"]
                            name = function["name"]
                            arguments = json.loads(function.get("arguments") or "{}")
                            print(f"\033[90m[Agent] Calling tool via MCP: {name}\033[0m")
                            result = await session.call_tool(name, arguments)
                            result_text = ""
                            if hasattr(result, "content") and result.content:
                                for c in result.content:
                                    if hasattr(c, "text"):
                                        result_text += c.text
                            print(f"\033[90m[Agent] Result: {result_text[:200]}\033[0m")
                            return result_text
                    conversation.append(assistant_message)
                    for call in tool_calls:
                        function = call["function"]
                        name = function["name"]
                        arguments = json.loads(function.get("arguments") or "{}")
                        print(f"\033[90m[Agent] Calling tool via MCP: {name}\033[0m")
                        result = await session.call_tool(name, arguments)
                        result_text = ""
                        if hasattr(result, "content") and result.content:
                            for c in result.content:
                                if hasattr(c, "text"):
                                    result_text += c.text
                        print(f"\033[90m[Agent] Result: {result_text[:200]}\033[0m")
                        conversation.append({
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": result_text,
                        })
                    continue

                final = message.get("content", "")
                print(f"\033[90m[Agent] Agent finished ({len(final)} chars)\033[0m")
                return final

            print("\033[91m[Agent] Max tool iterations reached\033[0m")
            return "Max tool iterations reached without final output."


def run_agent(topic: str, file_path: str = "") -> str:
    """Run the MQL agent for the given topic, optionally editing an existing file.

    Args:
        topic: Description of what to create or edit.
        file_path: Optional path to an existing .mq4/.mq5 file to edit.
    """
    if not topic or not topic.strip():
        return json.dumps({"status": "error", "message": "No topic provided."})
    print(f"\033[90m[Agent] {AGENT_NAME} | {PROVIDER.label} ({PROVIDER.model})\033[0m")
    return asyncio.run(_run_agent_async(topic, file_path))


def run_agent_payload(payload: dict) -> dict:
    """Run the MQL agent from a JSON payload.

    Payload keys: message (or topic), path (optional .mq4/.mq5 file to edit).
    """
    topic = payload.get("message") or payload.get("topic") or ""
    file_path = payload.get("path") or ""
    result = run_agent(topic, file_path)
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return {"status": "completed", "message": result}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=AGENT_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # Create a new EA from scratch\n"
            "  python main.py --topic \"Create an MQL5 moving average crossover EA with trailing stop\"\n\n"
            "  # Edit an existing file\n"
            "  python main.py --topic \"fix the syntax errors and add break-even logic\" --path ~/MT5/Experts/MyEA.mq5\n\n"
            "  # JSON mode with file editing\n"
            "  echo '{\"topic\":\"add RSI filter\",\"path\":\"/path/to/ea.mq5\"}' | python main.py --json\n"
        ),
    )
    parser.add_argument("--topic", type=str, default="", help="Describe the MQL script to create or edit.")
    parser.add_argument("--path", type=str, default="", help="Path to an existing .mq4/.mq5 file to edit (instead of creating from scratch).")
    parser.add_argument("--json", action="store_true", help="Accept JSON payload from stdin and output JSON.")
    args = parser.parse_args()

    if args.json:
        try:
            raw = sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            print(json.dumps({"status": "error", "message": f"Invalid JSON payload: {exc}"}))
            sys.exit(1)
        result = run_agent_payload(payload)
        print(json.dumps(result, ensure_ascii=False))
    else:
        file_path = args.path or ""
        if args.topic:
            print(f"\033[90m[Agent] Using topic: {args.topic[:100]}\033[0m")
        result = run_agent(args.topic, file_path)
        print(result)
