import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_REPORT = ROOT / ".github" / "scripts" / "ci_report.py"


def test_render_report_with_nonempty_checks(tmp_path: Path) -> None:
    test_metadata = tmp_path / "test-metadata.json"
    summary_file = tmp_path / "ci-summary.md"
    comment_file = tmp_path / "pr-comment.md"
    test_metadata.write_text(
        json.dumps(
            {
                "job": "test",
                "checks": [
                    {
                        "key": "pytest",
                        "label": "pytest",
                        "status": "success",
                        "log": "pytest.log",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(CI_REPORT),
            "render",
            "--test-metadata",
            str(test_metadata),
            "--summary-file",
            str(summary_file),
            "--comment-file",
            str(comment_file),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = summary_file.read_text(encoding="utf-8")
    assert "| test | SUCCESS |" in summary
    assert "| pytest | SUCCESS |" in summary
    assert comment_file.read_text(encoding="utf-8").startswith("<!-- ci-summary -->\n")
