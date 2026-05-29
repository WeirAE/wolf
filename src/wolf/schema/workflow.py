"""Top-level workflow configuration."""

from typing import Any


class WorkflowConfig:
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowConfig":
        """Construct from a pre-validated plain dict."""
        wf_d = data.get("workflow") or {}
        return cls(**wf_d)
