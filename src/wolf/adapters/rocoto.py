from __future__ import annotations
from pathlib import Path
from wolf.adapters.base import BaseAdapter


class RocotoAdapter(BaseAdapter):
    name = "rocoto"

    def translate(self, dag: "WolfDAG", config: "WorkflowConfig") -> dict[str, str]:
        root = self._realize(dag, config)
        return {"workflow.xml": root}

    def _validate(xml_file: Path | None) -> bool:
        pass

    def _realize(config: "WorkflowConfig") -> str:
        pass
