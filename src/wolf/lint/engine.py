from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wolf.schema.workflow import WorkflowConfig


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintIssue:
    def issue(self) -> str:
        return "placeholder"


@dataclass
class LintReport:
    def report(self) -> str:
        return "placeholder"


def run_lint(
    config: "WorkflowConfig", languages: list[str] | None = None
) -> LintReport:
    report = LintReport()
    return report
