# Useful macOS Terminal Commands

Open Terminal, go to the project folder, and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Clean outputs

Single log, clean detail view:

```bash
ci-log-analyzer samples/cmake_missing_dependency.log
```

Single log with nearby lines:

```bash
ci-log-analyzer samples/cmake_missing_dependency.log --show-context
```

All sample logs as a compact table:

```bash
ci-log-analyzer samples/ --only-failures
```

Directory scan with details:

```bash
ci-log-analyzer samples/ --only-failures --details
```

JSON report saved to a file:

```bash
ci-log-analyzer samples/ --format json > report.json
```

Text report saved to a file:

```bash
ci-log-analyzer samples/ --only-failures --details > report.txt
```

## Terminal readability tips

Clear the terminal:

```bash
clear
```

View long output page by page:

```bash
ci-log-analyzer samples/ --only-failures --details | less
```

Inside `less`:

- Press `Space` to move down one page.
- Press `b` to move back one page.
- Press `/word` to search.
- Press `q` to quit.
