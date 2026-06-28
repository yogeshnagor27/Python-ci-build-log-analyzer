# Python CI Build Log Analyzer

A small Python command-line tool that scans CI/build logs and reports the first actionable failure with a short root-cause summary.

It is useful when a build log is long and noisy: warnings, notes, summaries, and repeated downstream failures can hide the original error. This tool scans from the top, skips common noise, matches known failure patterns, and prints a structured result that is easy to read, export as JSON, or save as an HTML report.

## Architecture

```text
Log File / Directory
        |
        v
Command-line Interface (cli.py)
        |
        v
Analyzer (analyzer.py)
        |
        v
Rules Engine (rules.py + optional rules.yaml)
        |
        v
Failure Summary (models.py)
        |
        +--> Clean terminal output
        +--> JSON output
        +--> HTML report
```

## What it detects

- CMake configuration failures
- missing CMake packages/dependencies
- BitBake/Yocto recipe task failures
- BitBake fetch/SRC_URI failures
- C/C++ compilation errors
- linker errors
- permission issues
- Python script/runtime failures
- failed test stages
- Jenkins shell step failures
- GitHub Actions workflow step failures
- generic build errors
- optional project-specific rules from `rules.yaml`

## Example

Input log:

```text
warning: using cached SDK from previous build
+ mkdir -p /opt/releases/platform
mkdir: cannot create directory '/opt/releases/platform': Permission denied
script returned exit code 1
Finished: FAILURE
```

Output:

```text
CI Log Analyzer - Result
============================================================================
File        : samples/jenkins_permission_denied.log
Status      : FAIL
Source      : Linux/CI shell
Category    : permission_issue
Area        : Linux filesystem/process permissions
Confidence  : 0.87
Line        : 3
First error :
  mkdir: cannot create directory '/opt/releases/platform': Permission denied
Rule        : permission-denied

Next steps
----------------------------------------------------------------------------
1. Check file ownership, chmod executable bits, and workspace permissions.
2. Verify whether the CI user has access to mounted volumes, Docker socket, or cache directories.
3. Avoid running privileged operations unless the CI runner is configured for them.
```

## Project structure

```text
python-ci-build-log-analyzer/
├── src/ci_log_analyzer/
│   ├── analyzer.py          # core parsing logic
│   ├── cli.py               # command-line interface and terminal output
│   ├── html_report.py       # standalone HTML report generator
│   ├── models.py            # structured result model
│   ├── rules.py             # default detection rules and troubleshooting hints
│   └── rules_config.py      # optional YAML custom rule loader
├── samples/                 # safe sample CMake, BitBake, Jenkins, GitHub Actions logs
├── tests/                   # unit tests
├── docs/                    # demo output and design notes
├── rules.yaml               # example custom rules file
├── pyproject.toml
└── README.md
```

## Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development with pytest:

```bash
pip install -e ".[dev]"
```

## Usage

Analyze one log file:

```bash
ci-log-analyzer samples/cmake_missing_dependency.log
```

Show nearby lines around the detected error:

```bash
ci-log-analyzer samples/cmake_missing_dependency.log --show-context
```

Analyze a directory of logs with a clean summary table:

```bash
ci-log-analyzer samples/
```

Show only failed logs in the summary:

```bash
ci-log-analyzer samples/ --only-failures
```

Print detailed blocks for all logs in a directory:

```bash
ci-log-analyzer samples/ --details
```

Analyze nested directories:

```bash
ci-log-analyzer path/to/ci-logs --recursive
```

Return JSON output:

```bash
ci-log-analyzer samples/ --format json
```

Generate a standalone HTML report:

```bash
ci-log-analyzer samples/ --html-report reports/report.html
```

Use custom project-specific rules from YAML:

```bash
ci-log-analyzer samples/custom_platform_error.log --rules rules.yaml
```

Use as a CI quality gate and return exit code `2` when a failure is detected:

```bash
ci-log-analyzer build.log --fail-on-error
```

Analyze from stdin:

```bash
cat build.log | ci-log-analyzer
```

If the installed command is not available yet, use the Python module form:

```bash
python3 -m ci_log_analyzer samples/cmake_missing_dependency.log
```

## Sample logs included

The repository contains safe, fake, realistic sample logs for demonstration and tests:

- `samples/cmake_missing_dependency.log`
- `samples/cmake_generator_toolchain_failure.log`
- `samples/compiler_missing_header.log`
- `samples/linker_undefined_reference.log`
- `samples/bitbake_recipe_failure.log`
- `samples/bitbake_do_compile_failure.log`
- `samples/bitbake_do_fetch_failure.log`
- `samples/github_actions_pytest_failure.log`
- `samples/jenkins_permission_denied.log`
- `samples/no_actionable_error.log`
- `samples/custom_platform_error.log`

The tool is not limited to these samples. It can analyze any text-based build or CI log locally. Real private/company logs should not be committed to GitHub.

## Custom rules with `rules.yaml`

Default rules live in Python so the project works without external dependencies. Extra rules can be added through a YAML file:

```yaml
rules:
  - name: custom-platform-error
    pattern: "CUSTOM_PLATFORM_ERROR_[0-9]+"
    category: platform_specific_failure
    root_cause_area: Platform integration
    source: Custom CI
    confidence: 0.91
    suggested_steps:
      - "Open the platform integration log for the module that printed the custom error code."
      - "Check the failing component version, configuration, and environment variables."
```

Run it:

```bash
ci-log-analyzer samples/custom_platform_error.log --rules rules.yaml
```

Custom rules are evaluated before default rules so project-specific patterns can be detected before generic errors.

## JSON output example

```json
[
  {
    "file_path": "samples/bitbake_recipe_failure.log",
    "status": "failed",
    "category": "bitbake_recipe_failure",
    "root_cause_area": "BitBake/Yocto recipe task",
    "source": "BitBake/Yocto",
    "line_number": 10,
    "error_line": "ERROR: platform-service-1.4-r0 do_compile: oe_runmake failed",
    "matched_pattern": "bitbake-task-failed",
    "confidence": 0.95
  }
]
```

## Run tests

```bash
python3 -m unittest discover -s tests
```

Or, if dev dependencies are installed:

```bash
pytest
```

## How it works

1. Read a log file, directory, or stdin.
2. Split the log into lines.
3. Ignore common noise such as warnings, notes, debug lines, and `0 errors` summaries.
4. Match each remaining line against transparent regex-based rules.
5. Return the first actionable match with category, source, context, confidence, and suggested next steps.
6. Print a clean detail block for one log, a summary table for many logs, JSON for automation, or a standalone HTML report for sharing locally.

