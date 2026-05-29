"""
wolf.dag.engine

Built on graphlib. The DAG is constructed per-invocation from a
WorkflowConfig, used for validation and adapter input, then discarded.
"""

from __future__ import annotations

import multiprocessing as mp
import subprocess

from graphlib import TopologicalSorter, CycleError
from typing import Dict, Any
# from wolf.schema.workflow import WorkflowConfig, TaskConfig


class DAGBuilder:
    """
    Build a dependency graph from a list of config dictionaries.

    Each config dictionary is expected to have:
        - id: str
        - type: "compile" or "run"
        - parent: str or None
        - dependency: str or None
        - any other metadata needed by executors
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Map config_id → config_dict
        self.config_map = {t["id"]: t for t in config}

    # Private methods
    def _build_queue(self):
        topological_sorter = TopologicalSorter()
        task_queue = mp.Queue()
        finalized_task_queue = task_queue

        running_processes = {}

        def _run_task_in_process(taskcmd, node, finalized_task_queue):
            """
            Task executor. Fire off the command in a subprocess and wait
            for it to finish. Once done, put a receipt on the queue.
            """
            if isinstance(taskcmd, list):
                subprocess.check_call(taskcmd)
            else:
                # Only use shell=True if taskcmd is a trusted string
                subprocess.check_call(taskcmd, shell=True)
            finalized_task_queue.put(node)

        # add the nodes in the graph to the topological sorter
        for node, parents in self.config.items():
            if parents is None:
                topological_sorter.add(node, frozenset())
            else:
                topological_sorter.add(node, frozenset(parents))
        try:
            # mark the graph as finished and check for cycles in the graph
            topological_sorter.prepare()
            while topological_sorter.is_active():
                for node in topological_sorter.get_ready():
                    process = mp.Process(
                        target=_run_task_in_process,
                        args=(
                            self.config_map[node]["command"],
                            node,
                            finalized_task_queue,
                        ),
                    )
                    process.start()
                    running_processes[node] = process

                # retrieve each node as it completes and mark it as done
                node = finalized_task_queue.get()
                running_processes.pop(node).join()
                topological_sorter.done(node)
        except CycleError as e:
            print("Error: graph contains a cycle and is not a DAG")
            raise e
