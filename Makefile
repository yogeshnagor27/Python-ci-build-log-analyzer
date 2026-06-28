.PHONY: install test demo summary details json html custom clean

install:
	python3 -m pip install -e .

test:
	PYTHONPATH=src python3 -m unittest discover -s tests

demo:
	PYTHONPATH=src python3 -m ci_log_analyzer samples/cmake_missing_dependency.log

summary:
	PYTHONPATH=src python3 -m ci_log_analyzer samples/ --only-failures

details:
	PYTHONPATH=src python3 -m ci_log_analyzer samples/ --only-failures --details

json:
	PYTHONPATH=src python3 -m ci_log_analyzer samples/ --format json

html:
	mkdir -p reports
	PYTHONPATH=src python3 -m ci_log_analyzer samples/ --html-report reports/report.html

custom:
	PYTHONPATH=src python3 -m ci_log_analyzer samples/custom_platform_error.log --rules rules.yaml

clean:
	rm -rf .pytest_cache build dist *.egg-info src/*.egg-info reports
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
