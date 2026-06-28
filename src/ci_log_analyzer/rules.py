"""Detection rules for build, CI and Linux failure logs.

The project intentionally keeps rules transparent and easy to extend. In a real
team, these patterns can be tuned using historical CI failures from Jenkins,
GitHub Actions, GitLab CI, BitBake builds, and CMake/Ninja builds.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Pattern


@dataclass(frozen=True, slots=True)
class Rule:
    name: str
    pattern: Pattern[str]
    category: str
    root_cause_area: str
    source: str
    confidence: float
    suggested_steps: tuple[str, ...]


NOISE_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(r"\bwarning\b:?", re.IGNORECASE),
    re.compile(r"\bdeprecated\b", re.IGNORECASE),
    re.compile(r"\bnote\b:?", re.IGNORECASE),
    re.compile(r"\binfo\b:?", re.IGNORECASE),
    re.compile(r"\bDEBUG\b"),
    re.compile(r"\bexpected error\b", re.IGNORECASE),
    re.compile(r"\b0 errors?\b", re.IGNORECASE),
    re.compile(r"\berror summary: 0\b", re.IGNORECASE),
)

# Rules are evaluated line-by-line in this order. The analyzer returns the first
# actionable rule hit in log order, not the highest severity hit later in the log.
RULES: tuple[Rule, ...] = (
    Rule(
        name="cmake-missing-package",
        pattern=re.compile(r"Could not find (?:a package configuration file provided by )?[A-Za-z0-9_+.-]+|find_package\(.*\).*failed|No package '[^']+' found", re.IGNORECASE),
        category="missing_dependency",
        root_cause_area="CMake dependency resolution",
        source="CMake",
        confidence=0.94,
        suggested_steps=(
            "Install the missing development package or SDK on the build agent.",
            "Check CMAKE_PREFIX_PATH, package config files, and toolchain file paths.",
            "Confirm the dependency version expected by the target branch.",
        ),
    ),
    Rule(
        name="cmake-configuration-error",
        pattern=re.compile(r"CMake Error(?: at|:)|Configuring incomplete, errors occurred!", re.IGNORECASE),
        category="configuration_failure",
        root_cause_area="CMake configuration",
        source="CMake",
        confidence=0.90,
        suggested_steps=(
            "Open the CMake error context above this line and inspect the failing module or CMakeLists.txt entry.",
            "Delete stale CMake cache/build directory and reconfigure.",
            "Verify compiler, generator, and toolchain settings used by CI.",
        ),
    ),
    Rule(
        name="bitbake-task-failed",
        pattern=re.compile(r"ERROR:\s+Task \([^)]*\) failed with exit code|ERROR:\s+[^\s]+-\S+ do_(?!fetch\b)\w+:|ERROR:\s+Logfile of failure stored in:", re.IGNORECASE),
        category="bitbake_recipe_failure",
        root_cause_area="BitBake/Yocto recipe task",
        source="BitBake/Yocto",
        confidence=0.95,
        suggested_steps=(
            "Open the task logfile path printed by BitBake, usually temp/log.do_<task>.",
            "Check the failing recipe, layer priority, SRC_URI, patches, and do_compile/do_install implementation.",
            "Re-run the failing task with bitbake -c <task> -f <recipe> for a focused reproduction.",
        ),
    ),
    Rule(
        name="bitbake-fetcher-failure",
        pattern=re.compile(r"Fetcher failure|Unable to fetch URL|do_fetch.*failed|SRC_URI", re.IGNORECASE),
        category="source_fetch_failure",
        root_cause_area="BitBake source fetching",
        source="BitBake/Yocto",
        confidence=0.92,
        suggested_steps=(
            "Check network access, mirrors, credentials, branch names, and commit hashes.",
            "Verify SRC_URI and checksums in the recipe or bbappend.",
            "Try bitbake -c fetch <recipe> after cleaning the download cache if needed.",
        ),
    ),
    Rule(
        name="compiler-fatal-error",
        pattern=re.compile(r"fatal error: .*: No such file or directory|error: .* was not declared|error: expected .* before|error: no matching function", re.IGNORECASE),
        category="compilation_error",
        root_cause_area="C/C++ compilation",
        source="Compiler",
        confidence=0.89,
        suggested_steps=(
            "Inspect the source file and include path shown in the compiler output.",
            "Check whether headers, generated files, or feature flags are missing in CI.",
            "Build the same target locally with verbose output to compare include paths and definitions.",
        ),
    ),
    Rule(
        name="linker-error",
        pattern=re.compile(r"undefined reference to|ld(?:\.exe)?: error:|collect2: error: ld returned|cannot find -l", re.IGNORECASE),
        category="linker_error",
        root_cause_area="Linking/library resolution",
        source="Linker",
        confidence=0.88,
        suggested_steps=(
            "Check target_link_libraries/order of libraries and missing transitive dependencies.",
            "Verify that required libraries are built for the correct architecture/toolchain.",
            "Inspect CI artifact paths and linker search paths.",
        ),
    ),
    Rule(
        name="test-failure",
        pattern=re.compile(r"FAILED \[|AssertionError|\bFAILURES?\b|\d+ failed, \d+ passed|There were test failures", re.IGNORECASE),
        category="failed_test_stage",
        root_cause_area="Automated test execution",
        source="Test runner",
        confidence=0.84,
        suggested_steps=(
            "Open the first failing test case and compare expected vs actual behavior.",
            "Check recent commits touching the tested component.",
            "Re-run only the failing test with verbose logs and stable test data.",
        ),
    ),
    Rule(
        name="python-traceback",
        pattern=re.compile(r"Traceback \(most recent call last\):|ModuleNotFoundError:|ImportError:|FileNotFoundError:", re.IGNORECASE),
        category="python_runtime_error",
        root_cause_area="Python tooling/scripts",
        source="Python",
        confidence=0.86,
        suggested_steps=(
            "Read the final exception line in the traceback and inspect the script arguments.",
            "Verify virtual environment activation and dependency installation in CI.",
            "Check file paths and environment variables used by the Python step.",
        ),
    ),
    Rule(
        name="permission-denied",
        pattern=re.compile(r"Permission denied|Operation not permitted|EACCES", re.IGNORECASE),
        category="permission_issue",
        root_cause_area="Linux filesystem/process permissions",
        source="Linux/CI shell",
        confidence=0.87,
        suggested_steps=(
            "Check file ownership, chmod executable bits, and workspace permissions.",
            "Verify whether the CI user has access to mounted volumes, Docker socket, or cache directories.",
            "Avoid running privileged operations unless the CI runner is configured for them.",
        ),
    ),
    Rule(
        name="jenkins-shell-step-failed",
        pattern=re.compile(r"script returned exit code \d+|Build step .* marked build as failure|Finished: FAILURE", re.IGNORECASE),
        category="ci_stage_failure",
        root_cause_area="Jenkins pipeline shell stage",
        source="Jenkins",
        confidence=0.75,
        suggested_steps=(
            "Scroll upward to find the command that returned the non-zero exit code.",
            "Check environment variables and credentials injected into the Jenkins stage.",
            "Split large shell stages into smaller named steps for easier diagnosis.",
        ),
    ),
    Rule(
        name="github-actions-step-failed",
        pattern=re.compile(r"Process completed with exit code \d+|::error file=|Error: Process completed", re.IGNORECASE),
        category="ci_stage_failure",
        root_cause_area="GitHub Actions workflow step",
        source="GitHub Actions",
        confidence=0.76,
        suggested_steps=(
            "Check the previous command in the failing GitHub Actions step.",
            "Compare runner OS, dependency cache, and matrix values for passing vs failing jobs.",
            "Add explicit version pins and verbose logging around the failing command.",
        ),
    ),
    Rule(
        name="generic-error",
        pattern=re.compile(r"\berror:\b|\bERROR\b|\bfatal:\b", re.IGNORECASE),
        category="generic_error",
        root_cause_area="General build/CI failure",
        source="Unknown",
        confidence=0.55,
        suggested_steps=(
            "Inspect nearby lines for the command and component that produced the error.",
            "Re-run the failing stage with verbose logging enabled.",
            "Add a more specific rule if this error appears frequently in your CI environment.",
        ),
    ),
)
