"""Command line interface for the CI log analyzer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analyzer import analyze_log, analyze_text, iter_log_files
from .html_report import write_html_report
from .models import FailureSummary
from .rules import RULES, Rule
from .rules_config import RulesConfigError, load_rules_from_yaml


def _shorten(value: str | None, width: int) -> str:
    """Return a single-line string clipped to a fixed width."""
    text = (value or "-").replace("\t", " ").replace("\n", " ").strip()
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


def _status_label(status: str) -> str:
    return "FAIL" if status == "failed" else "OK/UNKNOWN"


def _load_rules_or_exit(parser: argparse.ArgumentParser, rules_path: str | None) -> tuple[Rule, ...]:
    """Return default rules plus optional custom rules from YAML."""
    if not rules_path:
        return RULES
    try:
        custom_rules = load_rules_from_yaml(rules_path)
    except RulesConfigError as exc:
        parser.error(str(exc))
    # Custom rules are evaluated before defaults so project-specific failures are
    # not swallowed by a generic error rule on the same line.
    return custom_rules + RULES


def _format_summary_table(summaries: list[FailureSummary], only_failures: bool = False) -> str:
    visible = [s for s in summaries if not only_failures or s.status == "failed"]
    failed_count = sum(1 for s in summaries if s.status == "failed")
    unknown_count = len(summaries) - failed_count

    lines: list[str] = []
    lines.append("CI Log Analyzer - Summary")
    lines.append("=" * 76)
    lines.append(f"Analyzed: {len(summaries)} log file(s) | Failed: {failed_count} | OK/Unknown: {unknown_count}")
    if only_failures:
        lines.append(f"Showing: failed files only ({len(visible)} item(s))")
    lines.append("")

    if not visible:
        lines.append("No matching log files to display.")
        return "\n".join(lines)

    header = f"{'#':>2}  {'Status':<10} {'Source':<15} {'Line':>5}  {'Category':<24} File"
    lines.append(header)
    lines.append("-" * len(header))
    for index, summary in enumerate(visible, start=1):
        line_number = str(summary.line_number) if summary.line_number is not None else "-"
        file_name = summary.file_path or "<stdin>"
        lines.append(
            f"{index:>2}  "
            f"{_status_label(summary.status):<10} "
            f"{_shorten(summary.source, 15):<15} "
            f"{line_number:>5}  "
            f"{_shorten(summary.category, 24):<24} "
            f"{_shorten(file_name, 48)}"
        )

    lines.append("")
    lines.append("Tip: run a single log path for full details, or add --details for detailed blocks.")
    return "\n".join(lines)


def _format_detail_block(summary: FailureSummary, show_context: bool = False, max_steps: int = 3) -> str:
    """Render one result in a cleaner human-readable layout."""
    title = summary.file_path or "<stdin>"
    lines: list[str] = []
    lines.append("CI Log Analyzer - Result")
    lines.append("=" * 76)
    lines.append(f"File        : {title}")
    lines.append(f"Status      : {_status_label(summary.status)}")
    lines.append(f"Source      : {summary.source}")
    lines.append(f"Category    : {summary.category}")
    lines.append(f"Area        : {summary.root_cause_area}")
    lines.append(f"Confidence  : {summary.confidence:.2f}")

    if summary.line_number is not None and summary.error_line:
        lines.append(f"Line        : {summary.line_number}")
        lines.append("First error :")
        lines.append(f"  {summary.error_line.strip()}")
    else:
        lines.append("Line        : -")
        lines.append("First error : No actionable error found")

    if summary.matched_pattern:
        lines.append(f"Rule        : {summary.matched_pattern}")

    if summary.ignored_earlier_noise:
        lines.append(f"Skipped     : {summary.ignored_earlier_noise} earlier warning/noise line(s)")

    if summary.suggested_steps:
        lines.append("")
        lines.append("Next steps")
        lines.append("-" * 76)
        for index, step in enumerate(summary.suggested_steps[:max_steps], start=1):
            lines.append(f"{index}. {step}")
        if len(summary.suggested_steps) > max_steps:
            lines.append(f"... {len(summary.suggested_steps) - max_steps} more step(s) hidden")

    if show_context and summary.context:
        lines.append("")
        lines.append("Nearby log lines")
        lines.append("-" * 76)
        lines.extend(summary.context)
    elif summary.context:
        lines.append("")
        lines.append("Tip: add --show-context to see nearby log lines around the error.")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ci-log-analyzer",
        description="Find the first real error in CMake, BitBake/Yocto, Jenkins, GitHub Actions and Linux CI logs.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Log files or directories. If omitted, stdin is analyzed.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan directories for .log, .txt, .out and .err files.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=3,
        help="Number of lines around the detected failure when --show-context is used. Default: 3.",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Show nearby log lines around the detected failure.",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Compatibility option. Context is hidden by default unless --show-context is used.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="When scanning multiple logs, print detailed result blocks after the summary table.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show only the summary table, even for a single log.",
    )
    parser.add_argument(
        "--only-failures",
        action="store_true",
        help="In summary output, hide logs that have no actionable error.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=3,
        help="Maximum troubleshooting steps shown in text output. Default: 3.",
    )
    parser.add_argument(
        "--html-report",
        metavar="PATH",
        help="Write a standalone HTML report to PATH after analysis.",
    )
    parser.add_argument(
        "--rules",
        metavar="PATH",
        help="Load additional regex detection rules from a YAML file. Custom rules are evaluated before default rules.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with code 2 if any analyzed log contains a detected failure.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rules = _load_rules_or_exit(parser, args.rules)

    summaries = []
    if args.paths:
        files = iter_log_files(args.paths, recursive=args.recursive)
        if not files:
            parser.error("No readable log files found. Pass a file path or use --recursive for nested directories.")
        for file_path in files:
            summaries.append(analyze_log(file_path, context_radius=args.context, rules=rules))
    else:
        summaries.append(analyze_text(sys.stdin.read(), file_path=None, context_radius=args.context, rules=rules))

    if args.format == "json":
        print(json.dumps([summary.to_dict() for summary in summaries], indent=2))
    else:
        if args.summary or len(summaries) > 1:
            print(_format_summary_table(summaries, only_failures=args.only_failures))
            if args.details:
                detail_summaries = [s for s in summaries if not args.only_failures or s.status == "failed"]
                for summary in detail_summaries:
                    print("\n" + "=" * 76 + "\n")
                    print(
                        _format_detail_block(
                            summary,
                            show_context=args.show_context and not args.no_context,
                            max_steps=args.max_steps,
                        )
                    )
        else:
            print(
                _format_detail_block(
                    summaries[0],
                    show_context=args.show_context and not args.no_context,
                    max_steps=args.max_steps,
                )
            )

    if args.html_report:
        report_path = write_html_report(summaries, args.html_report)
        print(f"HTML report written: {report_path}")

    has_failure = any(summary.status == "failed" for summary in summaries)
    return 2 if has_failure and args.fail_on_error else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
