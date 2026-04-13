import argparse
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _normalize_status(value: str | None) -> str:
    status = (value or "unknown").strip().lower()
    if status in {"success", "failure", "skipped", "cancelled", "timed_out", "pending"}:
        return status
    if not status:
        return "unknown"
    return status


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_lint_metadata(output: Path) -> None:
    payload = {
        "job": "lint",
        "checks": [
            {
                "key": "lint_sync",
                "label": "Lint dependency sync",
                "status": _normalize_status(os.getenv("SYNC_OUTCOME")),
                "log": "lint-sync.log",
            },
            {
                "key": "ruff_check",
                "label": "Ruff check",
                "status": _normalize_status(os.getenv("RUFF_CHECK_OUTCOME")),
                "log": "ruff-check.log",
            },
            {
                "key": "ruff_format",
                "label": "Ruff format check",
                "status": _normalize_status(os.getenv("RUFF_FORMAT_OUTCOME")),
                "log": "ruff-format.log",
            },
            {
                "key": "mypy",
                "label": "mypy",
                "status": _normalize_status(os.getenv("MYPY_OUTCOME")),
                "log": "mypy.log",
            },
        ],
    }
    _write_json(output, payload)


def write_test_metadata(output: Path) -> None:
    payload = {
        "job": "test",
        "checks": [
            {
                "key": "test_sync",
                "label": "Test dependency sync",
                "status": _normalize_status(os.getenv("SYNC_OUTCOME")),
                "log": "test-sync.log",
            },
            {
                "key": "pytest",
                "label": "pytest",
                "status": _normalize_status(os.getenv("PYTEST_OUTCOME")),
                "log": "pytest.log",
            },
        ],
        "coverage_file": "coverage.xml",
        "junit_file": "report.xml",
    }
    _write_json(output, payload)


def _load_metadata(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _render_status(value: str) -> str:
    mapping = {
        "success": "SUCCESS",
        "failure": "FAILURE",
        "skipped": "SKIPPED",
        "cancelled": "CANCELLED",
        "timed_out": "TIMED_OUT",
        "pending": "PENDING",
        "unknown": "UNKNOWN",
    }
    return mapping.get(value, value.upper())


def _compute_job_status(metadata: dict[str, Any] | None, fallback: str | None = None) -> str:
    if metadata is None:
        return _normalize_status(fallback)

    statuses = [_normalize_status(item.get("status")) for item in metadata.get("checks", [])]
    if any(status == "failure" for status in statuses):
        return "failure"
    if any(status == "cancelled" for status in statuses):
        return "cancelled"
    if any(status == "timed_out" for status in statuses):
        return "timed_out"
    if any(status == "pending" for status in statuses):
        return "pending"
    if any(status == "success" for status in statuses):
        return "success"
    if any(status == "skipped" for status in statuses):
        return "skipped"
    return _normalize_status(fallback)


def _tail_excerpt(path: Path, max_lines: int = 40, max_chars: int = 5000) -> str | None:
    if not path.exists():
        return None

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    trimmed = lines[-max_lines:]
    excerpt = "\n".join(trimmed).strip()
    if not excerpt:
        return None
    if len(excerpt) > max_chars:
        excerpt = excerpt[-max_chars:]
        excerpt = f"...\n{excerpt}"
    return excerpt


def _parse_xml_root(path: Path) -> ET.Element | None:
    if not path.exists():
        return None

    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError, ValueError):
        return None


def _parse_coverage(path: Path) -> dict[str, Any] | None:
    root = _parse_xml_root(path)
    if root is None:
        return None

    try:
        return {
            "line_rate": float(root.attrib.get("line-rate", 0.0)) * 100,
            "branch_rate": float(root.attrib.get("branch-rate", 0.0)) * 100,
            "lines_covered": int(root.attrib.get("lines-covered", 0)),
            "lines_valid": int(root.attrib.get("lines-valid", 0)),
            "branches_covered": int(root.attrib.get("branches-covered", 0)),
            "branches_valid": int(root.attrib.get("branches-valid", 0)),
        }
    except ValueError:
        return None


def _parse_junit(path: Path) -> dict[str, Any] | None:
    root = _parse_xml_root(path)
    if root is None:
        return None

    suites = [root] if root.tag.endswith("testsuite") else list(root.findall(".//testsuite"))
    if not suites:
        return None

    try:
        tests = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
        failures = sum(int(suite.attrib.get("failures", 0)) for suite in suites)
        errors = sum(int(suite.attrib.get("errors", 0)) for suite in suites)
        skipped = sum(int(suite.attrib.get("skipped", 0)) for suite in suites)
        duration = sum(float(suite.attrib.get("time", 0.0)) for suite in suites)

        if tests == 0 and root.attrib:
            tests = int(root.attrib.get("tests", 0))
            failures = int(root.attrib.get("failures", 0))
            errors = int(root.attrib.get("errors", 0))
            skipped = int(root.attrib.get("skipped", 0))
            duration = float(root.attrib.get("time", 0.0))

        return {
            "tests": tests,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
            "passed": max(tests - failures - errors - skipped, 0),
            "duration": duration,
        }
    except ValueError:
        return None


def _build_failure_sections(
    metadata: dict[str, Any] | None, title: str, base_dir: Path
) -> list[str]:
    if metadata is None:
        return []

    blocks: list[str] = []
    for check in metadata.get("checks", []):
        if _normalize_status(check.get("status")) != "failure":
            continue

        excerpt = _tail_excerpt(base_dir / check.get("log", ""))
        if excerpt is None:
            excerpt = "No log excerpt available."

        blocks.extend(
            [
                "<details>",
                f"<summary>{title}: {check.get('label')}</summary>",
                "",
                "~~~text",
                excerpt,
                "~~~",
                "</details>",
                "",
            ]
        )
    return blocks


def render_report(
    lint_metadata_path: Path | None,
    test_metadata_path: Path,
    summary_file: Path,
    comment_file: Path,
) -> None:
    lint_metadata = _load_metadata(lint_metadata_path)
    test_metadata = _load_metadata(test_metadata_path)

    lint_status = _compute_job_status(lint_metadata, os.getenv("LINT_JOB_CONCLUSION"))
    test_status = _compute_job_status(test_metadata, os.getenv("TEST_JOB_CONCLUSION"))

    run_url = (
        f"{os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}"
    )
    ref_name = os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME") or "unknown"
    sha = (os.getenv("GITHUB_SHA") or "")[:7]
    run_number = os.getenv("GITHUB_RUN_NUMBER", "")

    lines = [
        "## CI summary",
        "",
        f"Run: [checks #{run_number}]({run_url})",
        f"Ref: `{ref_name}` at `{sha}`",
        "",
        "| Job | Result |",
        "| --- | --- |",
        f"| lint | {_render_status(lint_status)} |",
        f"| test | {_render_status(test_status)} |",
        "",
    ]

    check_rows: list[str] = [
        "| Check | Result |",
        "| --- | --- |",
    ]
    for metadata in [lint_metadata, test_metadata]:
        if metadata is None:
            continue
        for check in metadata.get("checks", []):
            check_rows.append(
                f"| {check.get('label')} | {_render_status(_normalize_status(check.get('status')))} |"
            )
    if len(check_rows) > 2:
        lines.extend(["### Checks", ""])
        lines.extend(check_rows)
        lines.append("")
    elif lint_status != "success" or test_status != "success":
        lines.extend(
            [
                "Detailed artifacts were not fully available. Inspect the workflow run page for raw job logs.",
                "",
            ]
        )

    test_dir = test_metadata_path.parent
    coverage = (
        _parse_coverage(test_dir / str(test_metadata.get("coverage_file", "")))
        if test_metadata
        else None
    )
    junit = (
        _parse_junit(test_dir / str(test_metadata.get("junit_file", ""))) if test_metadata else None
    )

    if junit is not None:
        lines.extend(
            [
                "### Tests",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Total | {junit['tests']} |",
                f"| Passed | {junit['passed']} |",
                f"| Failed | {junit['failures']} |",
                f"| Errors | {junit['errors']} |",
                f"| Skipped | {junit['skipped']} |",
                f"| Duration, s | {junit['duration']:.2f} |",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### Tests",
                "",
                "Pytest JUnit report was not generated.",
                "",
            ]
        )

    if coverage is not None:
        lines.extend(
            [
                "### Coverage",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Line coverage | {coverage['line_rate']:.2f}% |",
                f"| Branch coverage | {coverage['branch_rate']:.2f}% |",
                f"| Lines covered | {coverage['lines_covered']} / {coverage['lines_valid']} |",
                f"| Branches covered | {coverage['branches_covered']} / {coverage['branches_valid']} |",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### Coverage",
                "",
                "Coverage report was not generated.",
                "",
            ]
        )

    lint_failure_sections = _build_failure_sections(
        lint_metadata,
        "lint",
        lint_metadata_path.parent if lint_metadata_path is not None else Path("."),
    )
    test_failure_sections = _build_failure_sections(test_metadata, "test", test_dir)
    failure_sections = lint_failure_sections + test_failure_sections

    if failure_sections:
        lines.extend(["### Failure excerpts", ""])
        lines.extend(failure_sections)
    else:
        lines.extend(["All reported checks passed.", ""])

    lines.append("Full logs and coverage artifacts are available on the workflow run page.")
    lines.append("")

    body = "\n".join(lines)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    comment_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(body, encoding="utf-8")
    comment_file.write_text(f"<!-- ci-summary -->\n{body}\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint_parser = subparsers.add_parser("write-lint-metadata")
    lint_parser.add_argument("--output", type=Path, required=True)

    test_parser = subparsers.add_parser("write-test-metadata")
    test_parser.add_argument("--output", type=Path, required=True)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--lint-metadata", type=Path, required=False)
    render_parser.add_argument("--test-metadata", type=Path, required=True)
    render_parser.add_argument("--summary-file", type=Path, required=True)
    render_parser.add_argument("--comment-file", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "write-lint-metadata":
        write_lint_metadata(args.output)
        return

    if args.command == "write-test-metadata":
        write_test_metadata(args.output)
        return

    render_report(args.lint_metadata, args.test_metadata, args.summary_file, args.comment_file)


if __name__ == "__main__":
    main()
