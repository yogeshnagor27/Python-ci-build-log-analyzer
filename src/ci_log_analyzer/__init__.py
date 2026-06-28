"""Python CI Build Log Analyzer.

A small, dependency-free toolkit for detecting the first actionable build failure
in CMake, BitBake/Yocto, Jenkins, GitHub Actions and Linux CI logs.
"""

from .analyzer import analyze_log, analyze_text
from .models import FailureSummary

__all__ = ["analyze_log", "analyze_text", "FailureSummary"]
__version__ = "0.2.0"
