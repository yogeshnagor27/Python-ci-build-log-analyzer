"""Standalone HTML report generation for CI log summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Sequence

from .models import FailureSummary


CSS = """
:root {
  --bg: #0f172a;
  --panel: #ffffff;
  --muted-panel: #f8fafc;
  --text: #172033;
  --muted: #667085;
  --border: #e4e7ec;
  --accent: #2563eb;
  --accent-soft: #eff6ff;
  --fail: #b42318;
  --fail-bg: #fef3f2;
  --ok: #067647;
  --ok-bg: #ecfdf3;
  --shadow: 0 18px 50px rgba(15, 23, 42, 0.16);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.20), transparent 30rem),
    linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #111827 100%);
  color: var(--text);
  min-height: 100vh;
}
main { max-width: 1460px; margin: 0 auto; padding: 26px 18px 38px; }
.hero {
  color: white;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
}
h1 { margin: 0 0 5px; font-size: clamp(26px, 3vw, 40px); letter-spacing: -0.04em; }
.subtitle { margin: 0; color: #cbd5e1; max-width: 760px; line-height: 1.45; font-size: 14px; }
.timestamp {
  flex: 0 0 auto;
  color: #dbeafe;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  backdrop-filter: blur(10px);
}
.dashboard {
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 22px;
  box-shadow: var(--shadow);
  overflow: hidden;
}
.cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: var(--border); }
.card { background: var(--panel); padding: 15px 18px; }
.card .label { color: var(--muted); font-size: 11px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
.card .value { font-size: 28px; font-weight: 850; margin-top: 3px; letter-spacing: -0.04em; line-height: 1.05; }
.card .hint { color: var(--muted); font-size: 12px; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card.fail .value { color: var(--fail); }
.card.ok .value { color: var(--ok); }
.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  background: var(--muted-panel);
}
.search {
  min-width: min(440px, 100%);
  flex: 1 1 360px;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  outline: none;
  background: white;
}
.search:focus { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12); }
.filters { display: flex; gap: 7px; flex-wrap: wrap; }
.filter-btn {
  border: 1px solid var(--border);
  background: white;
  color: #344054;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}
.filter-btn.active { background: var(--accent); border-color: var(--accent); color: white; }
.table-wrap { overflow-x: auto; }
table { width: 100%; min-width: 1080px; border-collapse: collapse; background: white; table-layout: fixed; }
col.index-col { width: 48px; }
col.status-col { width: 92px; }
col.source-col { width: 132px; }
col.category-col { width: 190px; }
col.file-col { width: 230px; }
col.error-col { width: auto; }
th, td { padding: 11px 14px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
th { background: #f9fafb; font-size: 11px; color: #475467; letter-spacing: .04em; text-transform: uppercase; white-space: nowrap; }
tr:hover td { background: #fbfdff; }
tr:last-child td { border-bottom: none; }
.index { color: var(--muted); font-weight: 800; }
.pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 11px;
  font-weight: 850;
  white-space: nowrap;
}
.pill.fail { background: var(--fail-bg); color: var(--fail); }
.pill.ok { background: var(--ok-bg); color: var(--ok); }
.source-pill { background: var(--accent-soft); color: #1d4ed8; max-width: 112px; overflow: hidden; text-overflow: ellipsis; }
.category { font-weight: 800; color: #344054; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.line-number { margin-top: 2px; color: var(--muted); font-size: 12px; }
.file-cell { min-width: 0; }
.file-name {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  font-weight: 750;
  color: #344054;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-folder {
  margin-top: 2px;
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.error-line {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.35;
  color: #1d2939;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 9px 11px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
details { margin-top: 8px; }
summary { cursor: pointer; color: var(--accent); font-weight: 800; font-size: 12px; }
.context {
  background: #111827;
  color: #e5e7eb;
  padding: 10px 12px;
  border-radius: 10px;
  overflow-x: auto;
  max-height: 210px;
  font-size: 11px;
  line-height: 1.5;
}
.steps { margin: 8px 0 0; padding-left: 18px; color: #475467; font-size: 12px; }
.steps li { margin-bottom: 4px; }
.empty-state { display: none; padding: 34px 22px; text-align: center; color: var(--muted); background: white; }
.bottom-space { height: 10px; background: white; }
@media (max-width: 900px) {
  main { padding: 20px 12px 34px; }
  .hero { display: block; }
  .timestamp { display: inline-flex; margin-top: 12px; }
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) { .cards { grid-template-columns: 1fr; } }
""".strip()


SCRIPT = """
const searchInput = document.querySelector('[data-search]');
const rows = Array.from(document.querySelectorAll('tbody tr'));
const buttons = Array.from(document.querySelectorAll('[data-filter]'));
const emptyState = document.querySelector('[data-empty-state]');
let activeFilter = 'all';

function updateRows() {
  const query = (searchInput.value || '').toLowerCase().trim();
  let visibleCount = 0;

  rows.forEach((row) => {
    const matchesFilter = activeFilter === 'all' || row.dataset.status === activeFilter;
    const matchesQuery = !query || row.innerText.toLowerCase().includes(query);
    const visible = matchesFilter && matchesQuery;
    row.style.display = visible ? '' : 'none';
    if (visible) visibleCount += 1;
  });

  emptyState.style.display = visibleCount ? 'none' : 'block';
}

buttons.forEach((button) => {
  button.addEventListener('click', () => {
    activeFilter = button.dataset.filter;
    buttons.forEach((item) => item.classList.remove('active'));
    button.classList.add('active');
    updateRows();
  });
});

searchInput.addEventListener('input', updateRows);
""".strip()


def _status(summary: FailureSummary) -> str:
    if summary.status == "failed":
        return '<span class="pill fail">FAIL</span>'
    return '<span class="pill ok">OK</span>'


def _steps(summary: FailureSummary) -> str:
    if not summary.suggested_steps:
        return ""
    items = "".join(f"<li>{escape(step)}</li>" for step in summary.suggested_steps[:4])
    return f'<ol class="steps">{items}</ol>'


def _context(summary: FailureSummary) -> str:
    parts: list[str] = []
    if summary.context:
        context = "\n".join(escape(line) for line in summary.context)
        parts.append(f'<details><summary>Context</summary><pre class="context">{context}</pre></details>')
    if summary.suggested_steps:
        parts.append(f'<details><summary>Next steps</summary>{_steps(summary)}</details>')
    return "".join(parts)


def _failure_rate(total: int, failed: int) -> str:
    if total == 0:
        return "0%"
    return f"{round((failed / total) * 100)}%"


def _file_parts(file_path: str | None) -> tuple[str, str, str]:
    if not file_path:
        return "<stdin>", "", "<stdin>"
    path = Path(file_path)
    name = path.name or file_path
    parent = str(path.parent)
    if parent in (".", ""):
        folder = ""
    else:
        folder = parent + "/"
    return name, folder, file_path


def render_html_report(summaries: Sequence[FailureSummary], title: str = "CI Log Analysis Dashboard") -> str:
    """Return an HTML report for one or more analysis summaries."""
    total = len(summaries)
    failed = sum(1 for summary in summaries if summary.status == "failed")
    ok_unknown = total - failed
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows: list[str] = []
    for index, summary in enumerate(summaries, start=1):
        line_number = str(summary.line_number) if summary.line_number is not None else "-"
        error_line = escape(summary.error_line or "No actionable error found")
        status_key = "failed" if summary.status == "failed" else "ok"
        file_name, file_folder, full_file_path = _file_parts(summary.file_path)
        rows.append(
            f'<tr data-status="{status_key}">'
            f'<td class="index">{index}</td>'
            f"<td>{_status(summary)}</td>"
            f'<td><span class="pill source-pill">{escape(summary.source)}</span></td>'
            f'<td><div class="category" title="{escape(summary.category)}">{escape(summary.category)}</div><div class="line-number">Line {line_number}</div></td>'
            f'<td class="file-cell" title="{escape(full_file_path)}"><div class="file-name">{escape(file_name)}</div><div class="file-folder">{escape(file_folder)}</div></td>'
            f'<td><div class="error-line">{error_line}</div>{_context(summary)}</td>'
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
<main>
  <section class="hero">
    <div>
      <h1>{escape(title)}</h1>
      <p class="subtitle">Build and CI log summary with first-error detection, categories, and debugging hints.</p>
    </div>
    <div class="timestamp">{generated}</div>
  </section>

  <section class="dashboard">
    <section class="cards">
      <div class="card"><div class="label">Analyzed</div><div class="value">{total}</div><div class="hint">logs scanned</div></div>
      <div class="card fail"><div class="label">Failures</div><div class="value">{failed}</div><div class="hint">actionable errors</div></div>
      <div class="card ok"><div class="label">OK / Unknown</div><div class="value">{ok_unknown}</div><div class="hint">no match found</div></div>
      <div class="card"><div class="label">Failure rate</div><div class="value">{_failure_rate(total, failed)}</div><div class="hint">from scanned logs</div></div>
    </section>

    <section class="toolbar">
      <input class="search" data-search type="search" placeholder="Search by file, source, category, or error...">
      <div class="filters" aria-label="Status filters">
        <button class="filter-btn active" data-filter="all" type="button">All</button>
        <button class="filter-btn" data-filter="failed" type="button">Failures</button>
        <button class="filter-btn" data-filter="ok" type="button">OK</button>
      </div>
    </section>

    <div class="table-wrap">
      <table>
        <colgroup>
          <col class="index-col">
          <col class="status-col">
          <col class="source-col">
          <col class="category-col">
          <col class="file-col">
          <col class="error-col">
        </colgroup>
        <thead>
          <tr>
            <th>#</th><th>Status</th><th>Source</th><th>Category</th><th>File</th><th>First actionable error</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    <div class="empty-state" data-empty-state>No results match the current filter.</div>
    <div class="bottom-space"></div>
  </section>
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""


def write_html_report(summaries: Sequence[FailureSummary], output_path: str | Path, title: str = "CI Log Analysis Dashboard") -> Path:
    """Write an HTML report and return the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html_report(summaries, title=title), encoding="utf-8")
    return path
