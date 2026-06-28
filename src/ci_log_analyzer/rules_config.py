"""Load optional external detection rules from a small YAML rules file.

The project keeps the default rules in Python for reliability, but users can add
extra organization/project-specific patterns without changing source code:

    ci-log-analyzer build.log --rules rules.yaml

PyYAML is used when it is installed. If it is not available, a small fallback
parser supports the simple rules.yaml structure used by this repository.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .rules import Rule


class RulesConfigError(ValueError):
    """Raised when an external rules file cannot be parsed or validated."""


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by this project.

    Supported structure:

    rules:
      - name: example
        pattern: "some regex"
        category: example_category
        root_cause_area: Example area
        source: Example source
        confidence: 0.80
        suggested_steps:
          - "First step"
          - "Second step"

    This is not a full YAML parser. It exists so the project has no runtime
    dependency for a simple config file use case.
    """
    rules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_list_key: str | None = None
    saw_rules_header = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "rules:":
            saw_rules_header = True
            continue

        if stripped.startswith("- ") and current_list_key is None:
            if not saw_rules_header:
                raise RulesConfigError("rules.yaml must start with a 'rules:' section")
            current = {}
            rules.append(current)
            item = stripped[2:].strip()
            if item:
                if ":" not in item:
                    raise RulesConfigError(f"Invalid rule line: {raw_line}")
                key, value = item.split(":", 1)
                current[key.strip()] = _strip_quotes(value)
            continue

        if current is None:
            raise RulesConfigError(f"Rule entry found before '- name': {raw_line}")

        if stripped.startswith("- ") and current_list_key is not None:
            current.setdefault(current_list_key, []).append(_strip_quotes(stripped[2:].strip()))
            continue

        if ":" not in stripped:
            raise RulesConfigError(f"Invalid rules.yaml line: {raw_line}")

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value == "":
            current[key] = []
            current_list_key = key
        else:
            current[key] = _strip_quotes(value)
            current_list_key = None

    return {"rules": rules}


def _load_yaml_data(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")

    try:  # Prefer PyYAML when available, but do not require it.
        import yaml  # type: ignore
    except Exception:
        return _parse_simple_yaml(text)

    loaded = yaml.safe_load(text)
    if loaded is None:
        return {"rules": []}
    if not isinstance(loaded, dict):
        raise RulesConfigError("rules.yaml root must be a mapping with a 'rules' key")
    return loaded


def load_rules_from_yaml(path: str | Path) -> tuple[Rule, ...]:
    """Load custom regex rules from a YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise RulesConfigError(f"Rules file not found: {config_path}")

    data = _load_yaml_data(config_path)
    raw_rules = data.get("rules", [])
    if not isinstance(raw_rules, list):
        raise RulesConfigError("rules.yaml field 'rules' must be a list")

    required = {"name", "pattern", "category", "root_cause_area", "source"}
    result: list[Rule] = []

    for index, raw_rule in enumerate(raw_rules, start=1):
        if not isinstance(raw_rule, dict):
            raise RulesConfigError(f"Rule #{index} must be a mapping")

        missing = sorted(required - set(raw_rule))
        if missing:
            raise RulesConfigError(f"Rule #{index} is missing required field(s): {', '.join(missing)}")

        try:
            pattern = re.compile(str(raw_rule["pattern"]), re.IGNORECASE)
        except re.error as exc:
            raise RulesConfigError(f"Rule #{index} has an invalid regex pattern: {exc}") from exc

        steps = raw_rule.get("suggested_steps", [])
        if isinstance(steps, str):
            steps = [steps]
        if not isinstance(steps, list):
            raise RulesConfigError(f"Rule #{index} field 'suggested_steps' must be a list or string")

        try:
            confidence = float(raw_rule.get("confidence", 0.80))
        except (TypeError, ValueError) as exc:
            raise RulesConfigError(f"Rule #{index} field 'confidence' must be numeric") from exc

        result.append(
            Rule(
                name=str(raw_rule["name"]),
                pattern=pattern,
                category=str(raw_rule["category"]),
                root_cause_area=str(raw_rule["root_cause_area"]),
                source=str(raw_rule["source"]),
                confidence=confidence,
                suggested_steps=tuple(str(step) for step in steps),
            )
        )

    return tuple(result)
