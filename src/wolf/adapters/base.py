"""
Abstract classes for adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from wolf.dag.engine import WorkflowDAG
from wolf.schema.workflow import WorkflowConfig

class BaseAdapter(ABC):
    def __init__(self, config:WorkflowConfig, dag: WorkflowDAG) -> None:
        self.config = config
        self.dag = dag
    
    @abstractmethod
    def translate(self):
        return[]

    def validate(self):
        return[]