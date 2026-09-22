"""Read-only code-audit tools. All operate over a Corpus; no shell, no network."""
from dataclasses import dataclass, field

from ..corpus.base import Finding


@dataclass
class ToolContext:
    corpus: object
    findings: list = field(default_factory=list)
    done: bool = False


def list_files(ctx: ToolContext) -> str:
    return "\n".join(ctx.corpus.files())


def read_file(ctx: ToolContext, path: str, start: int = None, end: int = None) -> str:
    return ctx.corpus.read(path, start, end)


def search_code(ctx: ToolContext, pattern: str) -> str:
    matches = ctx.corpus.search(pattern)
    if not matches:
        return "(no matches)"
    return "\n".join(f"{m['file']}:{m['line']}: {m['text']}" for m in matches)


def report_finding(ctx: ToolContext, file: str, line: int, vuln_type: str,
                   description: str, cwe_guess: str = "", confidence: float = 0.5) -> str:
    ctx.findings.append(Finding(
        file=file, line=int(line), vuln_type=vuln_type, description=description,
        cwe_guess=cwe_guess, confidence=float(confidence),
    ))
    return f"recorded finding: {file}:{line} ({vuln_type})"


def done(ctx: ToolContext, summary: str = "") -> str:
    ctx.done = True
    return "audit finished"
