"""Data models used by the CI log analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(slots=True)
class FailureSummary:
    """Structured result returned by the analyzer.

    Attributes:
        file_path: The analyzed log file path, if available.
        status: "failed" when a meaningful failure was found, otherwise "passed_or_unknown".
        category: High-level failure category.
        root_cause_area: Human-friendly subsystem/area likely responsible.
        source: Build ecosystem/source that produced the failure.
        line_number: 1-based line number for the first actionable error.
        error_line: The original log line that matched.
        matched_pattern: Name of the rule that detected the failure.
        confidence: A simple confidence score from 0.0 to 1.0.
        suggested_steps: Practical next debugging steps.
        context: Small group of lines around the failure.
        ignored_earlier_noise: Number of earlier warning/noise lines skipped.
    """

    file_path: str | None
    status: str
    category: str
    root_cause_area: str
    source: str
    line_number: int | None
    error_line: str | None
    matched_pattern: str | None
    confidence: float
    suggested_steps: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)
    ignored_earlier_noise: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return asdict(self)

    def to_text(self, show_context: bool = True) -> str:
        """Render the summary in a readable CLI format."""
        lines: list[str] = []
        title = self.file_path or "<stdin>"
        lines.append(f"Log: {title}")
        lines.append(f"Status: {self.status}")
        lines.append(f"Category: {self.category}")
        lines.append(f"Source: {self.source}")
        lines.append(f"Root cause area: {self.root_cause_area}")
        lines.append(f"Confidence: {self.confidence:.2f}")

        if self.line_number is not None and self.error_line:
            lines.append(f"First real error: line {self.line_number}")
            lines.append(f"> {self.error_line.strip()}")
        else:
            lines.append("First real error: not found")

        if self.matched_pattern:
            lines.append(f"Matched rule: {self.matched_pattern}")

        if self.ignored_earlier_noise:
            lines.append(f"Ignored earlier noise/warnings: {self.ignored_earlier_noise}")

        if self.suggested_steps:
            lines.append("Suggested troubleshooting steps:")
            for index, step in enumerate(self.suggested_steps, start=1):
                lines.append(f"  {index}. {step}")

        if show_context and self.context:
            lines.append("Context:")
            lines.extend(f"  {line.rstrip()}" for line in self.context)

        return "\n".join(lines)
