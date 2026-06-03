"""
Abstract classes for adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from wolf.dag.engine import DAGBuilder
from wolf.schema.workflow import WorkflowConfig


class BaseAdapter(ABC):
    """
    placeholder base adapter
    """
    def __init__(self, config: WorkflowConfig, dag: DAGBuilder) -> None:
        self.config = config
        self.dag = dag

    @abstractmethod
    def translate(self, dag, config):
        return []

    @abstractmethod
    def realize(self, dag, config):
        return []

    @abstractmethod
    def validate(self, xml_file):
        return []
