"""Shared data types for the corpus + scoring layer."""
from dataclasses import dataclass, field


@dataclass
class Vuln:
    """A ground-truth vulnerability (from ground_truth.yaml)."""
    id: str
    file: str
    line_start: int
    line_end: int
    cwe: str
    desc: str
    keywords: list


@dataclass
class Finding:
    """A vulnerability reported by an arm (baseline or harness)."""
    file: str
    line: int
    vuln_type: str
    description: str
    cwe_guess: str = ""
    confidence: float = 0.5
    kept_by_verifier: bool = True


@dataclass
class ScoreResult:
    matched: list = field(default_factory=list)          # (Finding, Vuln) pairs
    missed: list = field(default_factory=list)           # Vuln
    false_positives: list = field(default_factory=list)  # Finding
    recall: float = 0.0
    precision: float = 0.0
    f1: float = 0.0
