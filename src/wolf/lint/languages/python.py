from __future__ import annotations
import json
from pathlib import Path
from wolf.lint.engine import LintIssue, Severity
from wolf.lint.languages.base import BaseLinter


class PythonLinter(BaseLinter):
    tool_name = "ruff"

    def lint(self, path: Path) -> list[LintIssue]:
        if not self.is_available():
            return [self._unavailable(path)]
        _, stdout, _ = self._run(["ruff", "check", "--output-format=json", str(path)])
        try:
            data = json.loads(stdout) if stdout.strip() else []
        except json.JSONDecodeError:
            return []
        return [
            LintIssue(
                file=i.get("filename", str(path)),
                line=i.get("location", {}).get("row"),
                col=i.get("location", {}).get("column"),
                code=i.get("code", "R000"),
                message=i.get("message", ""),
                severity=Severity.ERROR,
                source="ruff",
            )
            for i in data
        ]
