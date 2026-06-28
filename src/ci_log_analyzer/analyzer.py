"""Core analyzer implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from .models import FailureSummary
from .rules import NOISE_PATTERNS, RULES, Rule


def _is_noise(line: str) -> bool:
    """Return True for warnings/noisy lines that should not be treated as first real errors."""
    stripped = line.strip()
    if not stripped:
        return True
    return any(pattern.search(stripped) for pattern in NOISE_PATTERNS)


def _context(lines: list[str], index: int, radius: int = 3) -> list[str]:
    start = max(index - radius, 0)
    end = min(index + radius + 1, len(lines))
    result: list[str] = []
    for line_index in range(start, end):
        prefix = ">>" if line_index == index else "  "
        result.append(f"{prefix} {line_index + 1}: {lines[line_index].rstrip()}")
    return result


def _match_rule(line: str, rules: Sequence[Rule] = RULES) -> Rule | None:
    for rule in rules:
        if rule.pattern.search(line):
            return rule
    return None


def analyze_text(
    text: str,
    file_path: str | None = None,
    context_radius: int = 3,
    rules: Sequence[Rule] = RULES,
) -> FailureSummary:
    """Analyze log text and return a structured failure summary.

    The analyzer scans from the top of the log and returns the first line that
    matches a known actionable failure rule. Warnings, notes, informational lines,
    and explicit "0 errors" messages are counted as noise and skipped.
    """
    lines = text.splitlines()
    ignored_noise = 0

    for index, line in enumerate(lines):
        if _is_noise(line):
            # Count only noisy lines that look error-ish enough to matter.
            lowered = line.lower()
            if "error" in lowered or "warning" in lowered or "deprecated" in lowered:
                ignored_noise += 1
            continue

        rule = _match_rule(line, rules=rules)
        if rule is None:
            continue

        return FailureSummary(
            file_path=file_path,
            status="failed",
            category=rule.category,
            root_cause_area=rule.root_cause_area,
            source=rule.source,
            line_number=index + 1,
            error_line=line.rstrip(),
            matched_pattern=rule.name,
            confidence=rule.confidence,
            suggested_steps=list(rule.suggested_steps),
            context=_context(lines, index, radius=context_radius),
            ignored_earlier_noise=ignored_noise,
        )

    return FailureSummary(
        file_path=file_path,
        status="passed_or_unknown",
        category="no_actionable_error_found",
        root_cause_area="Unknown",
        source="Unknown",
        line_number=None,
        error_line=None,
        matched_pattern=None,
        confidence=0.0,
        suggested_steps=[
            "Check whether the log was truncated before the failing section.",
            "Search for failed commands, non-zero exit codes, or generated task-specific logs.",
            "Add a custom detection rule if your team uses project-specific error formats.",
        ],
        context=[],
        ignored_earlier_noise=ignored_noise,
    )


def analyze_log(
    path: str | Path,
    context_radius: int = 3,
    encoding: str = "utf-8",
    rules: Sequence[Rule] = RULES,
) -> FailureSummary:
    """Analyze a log file from disk."""
    file_path = Path(path)
    text = file_path.read_text(encoding=encoding, errors="replace")
    return analyze_text(text, file_path=str(file_path), context_radius=context_radius, rules=rules)


def iter_log_files(paths: Iterable[str | Path], recursive: bool = False) -> list[Path]:
    """Expand files/directories into a sorted list of candidate log files."""
    candidates: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file():
            candidates.append(path)
            continue
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in path.glob(pattern):
                if child.is_file() and child.suffix.lower() in {".log", ".txt", ".out", ".err"}:
                    candidates.append(child)
    return sorted(set(candidates))
