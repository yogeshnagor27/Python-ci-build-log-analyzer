from pathlib import Path
import sys
import tempfile
import unittest

# Allow tests to run directly from a fresh checkout before the package is installed.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ci_log_analyzer import analyze_log, analyze_text
from ci_log_analyzer.html_report import write_html_report
from ci_log_analyzer.rules import RULES
from ci_log_analyzer.rules_config import load_rules_from_yaml

SAMPLES = ROOT / "samples"


class TestCiLogAnalyzer(unittest.TestCase):
    def test_detects_cmake_configuration_error(self):
        summary = analyze_log(SAMPLES / "cmake_missing_dependency.log")
        self.assertEqual(summary.status, "failed")
        self.assertIn(summary.category, {"configuration_failure", "missing_dependency"})
        self.assertEqual(summary.source, "CMake")
        self.assertIsNotNone(summary.line_number)
        self.assertIn("CMake", summary.error_line)

    def test_detects_cmake_toolchain_failure(self):
        summary = analyze_log(SAMPLES / "cmake_generator_toolchain_failure.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "configuration_failure")
        self.assertEqual(summary.source, "CMake")

    def test_detects_bitbake_recipe_failure(self):
        summary = analyze_log(SAMPLES / "bitbake_recipe_failure.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "bitbake_recipe_failure")
        self.assertEqual(summary.source, "BitBake/Yocto")
        self.assertIn("do_compile", summary.error_line)

    def test_detects_bitbake_fetch_failure(self):
        summary = analyze_log(SAMPLES / "bitbake_do_fetch_failure.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "source_fetch_failure")
        self.assertEqual(summary.source, "BitBake/Yocto")
        self.assertIn("Fetcher failure", summary.error_line)

    def test_detects_compiler_error_inside_bitbake_compile_log(self):
        summary = analyze_log(SAMPLES / "bitbake_do_compile_failure.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "compilation_error")
        self.assertEqual(summary.source, "Compiler")
        self.assertIn("No such file or directory", summary.error_line)

    def test_detects_test_failure_before_github_actions_exit_code(self):
        summary = analyze_log(SAMPLES / "github_actions_pytest_failure.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "failed_test_stage")
        self.assertEqual(summary.source, "Test runner")
        self.assertIn("FAILURES", summary.error_line)

    def test_detects_permission_denied_before_jenkins_exit_code(self):
        summary = analyze_log(SAMPLES / "jenkins_permission_denied.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "permission_issue")
        self.assertEqual(summary.source, "Linux/CI shell")
        self.assertIn("Permission denied", summary.error_line)

    def test_detects_compiler_missing_header(self):
        summary = analyze_log(SAMPLES / "compiler_missing_header.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "compilation_error")
        self.assertEqual(summary.source, "Compiler")
        self.assertIn("No such file or directory", summary.error_line)

    def test_detects_linker_error(self):
        summary = analyze_log(SAMPLES / "linker_undefined_reference.log")
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "linker_error")
        self.assertEqual(summary.source, "Linker")
        self.assertIn("undefined reference", summary.error_line)

    def test_returns_unknown_when_no_actionable_error(self):
        summary = analyze_log(SAMPLES / "no_actionable_error.log")
        self.assertEqual(summary.status, "passed_or_unknown")
        self.assertEqual(summary.category, "no_actionable_error_found")
        self.assertIsNone(summary.line_number)

    def test_analyze_text_stdin_style_input(self):
        text = "warning: harmless\nCMake Error at src/CMakeLists.txt:10 (add_subdirectory): missing path"
        summary = analyze_text(text)
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.line_number, 2)
        self.assertGreaterEqual(summary.ignored_earlier_noise, 1)

    def test_loads_custom_yaml_rules(self):
        custom_rules = load_rules_from_yaml(ROOT / "rules.yaml")
        summary = analyze_log(SAMPLES / "custom_platform_error.log", rules=custom_rules + RULES)
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.category, "platform_specific_failure")
        self.assertEqual(summary.source, "Custom CI")
        self.assertEqual(summary.matched_pattern, "custom-platform-error")

    def test_writes_html_report(self):
        summary = analyze_log(SAMPLES / "linker_undefined_reference.log")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.html"
            write_html_report([summary], out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("CI Log Analysis Dashboard", content)
            self.assertIn("linker_error", content)
            self.assertIn("undefined reference", content)
            self.assertIn("CI Log Analysis Dashboard", content)
            self.assertIn("Search by file", content)


if __name__ == "__main__":
    unittest.main()
