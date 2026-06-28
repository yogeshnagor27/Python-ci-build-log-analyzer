# Design Notes

## Goal

The goal is not to replace a full observability platform. The goal is to solve one practical developer problem:

> Given a long CI/build log, find the first actionable error quickly.

This is useful because the last line of a build log is often generic, such as `Finished: FAILURE` or `Process completed with exit code 1`. The root cause is usually earlier.

## Pipeline

```text
Log File / Directory -> CLI -> Analyzer -> Rules Engine -> Failure Summary -> Text / JSON / HTML
```

## Why rule-based?

This project uses regex-based rules because they are:

- simple to inspect
- easy to test
- easy to extend
- deterministic in CI
- dependency-free by default

This is better for a small engineering tool than a black-box model because users can see exactly why a line matched.

## Why optional rules.yaml?

Default rules cover common CMake, BitBake/Yocto, Jenkins, GitHub Actions, compiler, linker, and Linux shell errors. Real teams often have project-specific error codes. The optional `rules.yaml` file allows users to add those patterns without editing Python source code.

## First actionable error vs last error

The analyzer scans top-to-bottom and returns the first actionable rule match. It intentionally skips warnings, notes, debug lines, and `0 errors` summaries. This makes the output useful for root-cause analysis instead of merely reporting the final failure status.

## Current limitations

- It is rule-based, so unknown patterns may be missed.
- It does not parse binary logs.
- It does not connect to Jenkins/GitHub APIs directly.
- It does not execute CMake, BitBake, or tests. It analyzes their logs.
- It does not sanitize private logs automatically.

## Future improvements

- More sample logs and rule coverage
- HTML report filtering/search
- SARIF output for code-scanning tools
- GitLab CI support examples
- Automatic secret/path redaction for private logs
- Rule severity levels
- More structured category taxonomy
