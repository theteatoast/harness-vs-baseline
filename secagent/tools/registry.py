"""Tool registry for the parse-based action protocol.

The worker is prompted with describe_tools() and replies with a JSON object
{"action": <name>, "args": {...}}. dispatch() runs it against the ToolContext.
This avoids relying on any provider's native function-calling, so the harness
works identically across frontier and cheaper open models.
"""
from . import code

TOOLS = {
    "list_files": {
        "fn": code.list_files, "args": {},
        "desc": "List the in-scope source files.",
    },
    "read_file": {
        "fn": code.read_file, "args": {"path": "str", "start": "int?", "end": "int?"},
        "desc": "Read a file (optionally a line range); returned with line numbers.",
    },
    "search_code": {
        "fn": code.search_code, "args": {"pattern": "str (regex)"},
        "desc": "Regex-search across all in-scope files.",
    },
    "report_finding": {
        "fn": code.report_finding,
        "args": {"file": "str", "line": "int", "vuln_type": "str",
                 "description": "str", "cwe_guess": "str?", "confidence": "float 0-1?"},
        "desc": "Record one vulnerability you have confirmed.",
    },
    "done": {
        "fn": code.done, "args": {"summary": "str?"},
        "desc": "Finish the audit when you have covered all in-scope files.",
    },
}


def describe_tools() -> str:
    lines = []
    for name, t in TOOLS.items():
        args = ", ".join(f"{k}: {v}" for k, v in t["args"].items()) or "(none)"
        lines.append(f"- {name}({args}) — {t['desc']}")
    return "\n".join(lines)


def dispatch(ctx, action: dict) -> str:
    name = action.get("action")
    if name not in TOOLS:
        return f"error: unknown action {name!r} (valid: {', '.join(TOOLS)})"
    try:
        return TOOLS[name]["fn"](ctx, **(action.get("args") or {}))
    except TypeError as e:
        return f"error calling {name}: {e}"
