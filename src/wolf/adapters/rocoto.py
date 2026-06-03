from __future__ import annotations
from pathlib import Path
from wolf.adapters.base import BaseAdapter
from wolf.schema.workflow import WorkflowConfig
from wolf.dag.engine import DAGBuilder as WolfDAG


class RocotoAdapter(BaseAdapter):
    """
    placeholder adapter for Rocoto
    """
    name = "rocoto"

    def translate(self, dag: "WolfDAG", config: "WorkflowConfig") -> dict[str, str]:
        """
        placeholder template translator
        """
        root = self._realize(dag, config)
        return {"workflow.xml": root}

    def _validate(self, xml_file: Path | None) -> bool:
        """
        placeholder template validator
        """
        return xml_file

    def _realize(self, dag, config: "WorkflowConfig") -> str:
        """
        placeholder template realization
        """
        return config
