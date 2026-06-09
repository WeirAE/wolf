from __future__ import annotations
import abc
import shutil
import subprocess
from pathlib import Path
from wolf.lint.engine import LintIssue, Severity


class BaseLinter(abc.ABC):
    tool_name: str = "unknown"

    def is_available(self) -> bool:
        return shutil.which(self.tool_name) is not None

    @abc.abstractmethod
    def lint(self, path: Path) -> list[LintIssue]: ...
    def _run(self, cmd: list[str]) -> tuple[int, str, str]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def _unavailable(self, path: Path) -> LintIssue:
        return LintIssue(
            file=str(path),
            line=None,
            col=None,
            code="WOLF001",
            message=f"Tool '{self.tool_name}' not found on PATH.",
            severity=Severity.WARNING,
            source=f"wolf:{self.tool_name}",
        )
