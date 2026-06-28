# Quickstart - macOS/Linux

## 1. Open Terminal and go to the project

```bash
cd ~/Downloads/python-ci-build-log-analyzer
```

Check that you are in the correct folder:

```bash
ls
```

You should see:

```text
README.md
pyproject.toml
src
samples
tests
```

## 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your terminal should show `(.venv)` at the start.

## 3. Install the project

```bash
python3 -m pip install -e .
```

## 4. Run one sample log

```bash
python3 -m ci_log_analyzer samples/cmake_missing_dependency.log
```

## 5. Run all sample logs in a clean table

```bash
python3 -m ci_log_analyzer samples/ --only-failures
```

## 6. Show detailed output

```bash
python3 -m ci_log_analyzer samples/ --only-failures --details
```

## 7. Generate an HTML report

```bash
mkdir -p reports
python3 -m ci_log_analyzer samples/ --html-report reports/report.html
open reports/report.html
```

## 8. Test custom rules from rules.yaml

```bash
python3 -m ci_log_analyzer samples/custom_platform_error.log --rules rules.yaml
```

## 9. Run tests

```bash
python3 -m unittest discover -s tests
```

## 10. If `ci-log-analyzer` says command not found

Use this form instead:

```bash
python3 -m ci_log_analyzer samples/cmake_missing_dependency.log
```

After `python3 -m pip install -e .` works, this command should also work:

```bash
ci-log-analyzer samples/cmake_missing_dependency.log
```
