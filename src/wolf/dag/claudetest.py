"""Workflow DAG engine backed exclusively by Python's stdlib graphlib.

Zero third-party dependencies. Designed for HPC portability.

Architecture (Separation of Concerns)::

    Task              — immutable value object; validates inputs at construction
    WorkflowGraph     — graph structure, validation, ordering, analysis
    AsciiRenderer     — human-readable visualisation (composes WorkflowGraph)
    DotExporter       — Graphviz DOT export (composes WorkflowGraph)

Trust boundary
--------------
``Task.__post_init__`` is the single trust boundary for all externally-sourced
data (YAML fields, CLI arguments, API responses).  Every field is validated
against an allowlist before the object is admitted to the domain model.
Downstream code — graph analysis, rendering, adapter compilation — operates
on data that is guaranteed clean by construction.

Security properties enforced at the boundary:

* Task names match ``_NAME_PATTERN``: alphanumeric + underscore, starts with a
  letter, 1–64 characters.  This simultaneously prevents shell injection,
  DOT injection, XML injection, and violating ECFlow/Cylc naming rules.
* Script paths match ``_SCRIPT_PATH_PATTERN``: Unix path characters only; no
  shell metacharacters (space, quote, semicolon, backtick, ``$``, ``|``, ``&``,
  ``>``, ``<``).  Safe to pass to ``subprocess`` without a shell.
* Numeric fields are bounds-checked: walltime and node counts cannot be zero,
  negative, or implausibly large.
* Dependency names are validated against the same name pattern as task names
  before the graph is even constructed.
"""

from __future__ import annotations

import graphlib
import re
from dataclasses import dataclass, field
from typing import NamedTuple


__all__ = [
    "Task",
    "WorkflowGraph",
    "AsciiRenderer",
    "DotExporter",
    "CriticalPath",
    "TaskInputError",
    "WorkflowCycleError",
    "WorkflowValidationError",
]


# ---------------------------------------------------------------------------
# Allowlist constants — single source of truth for all input validation
# ---------------------------------------------------------------------------

# Task names: letter-start, alphanumeric + underscore, 1–64 chars.
# Safe for: DOT node IDs, ECFlow task names, Cylc task names, shell variables.
_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")

# Script paths: standard Unix path characters only.
# Explicitly excludes shell metacharacters: space " ' ` ; $ | & > < ( ) \
# Max 255 chars matches POSIX PATH_MAX for a single component.
_SCRIPT_PATH_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_./:@\-]{1,255}$")

_MAX_WALLTIME_S: int = 604_800  # 7 days — hard upper bound
_MIN_WALLTIME_S: int = 1
_MAX_NODES: int = 100_000
_MIN_NODES: int = 1


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TaskInputError(ValueError):
    """Raised when a Task field fails allowlist validation.

    This is a trust-boundary error: the input arrived from an external
    source (YAML, CLI, API) and did not conform to the accepted format.
    It is distinct from ``WorkflowValidationError``, which concerns the
    structural integrity of the graph after all tasks are admitted.
    """


class WorkflowValidationError(ValueError):
    """Raised when the graph structure is invalid.

    Covers: duplicate task names, references to undeclared dependencies.
    These are structural errors detected after Task objects have already
    passed input validation.
    """


class WorkflowCycleError(ValueError):
    """Raised when the task dependency graph contains a cycle."""


# ---------------------------------------------------------------------------
# Input validation helpers — private; called only from Task.__post_init__
# ---------------------------------------------------------------------------


def _require_name(value: str, field_label: str) -> None:
    """Assert ``value`` matches the task name allowlist.

    Args:
        value: The string to validate.
        field_label: Human-readable label used in the error message.

    Raises:
        TaskInputError: If ``value`` does not match ``_NAME_PATTERN``.
    """
    if not _NAME_PATTERN.match(value):
        raise TaskInputError(
            f"{field_label} {value!r} is not a valid identifier. "
            f"Must match {_NAME_PATTERN.pattern}"
        )


def _require_script_path(value: str) -> None:
    """Assert ``value`` is a safe script path with no shell metacharacters.

    Args:
        value: The path string to validate.

    Raises:
        TaskInputError: If ``value`` contains disallowed characters or is empty.
    """
    if not _SCRIPT_PATH_PATTERN.match(value):
        raise TaskInputError(
            f"Script path {value!r} contains disallowed characters. "
            "Only alphanumerics, '.', '/', '_', ':', '@', and '-' are permitted. "
            "Shell metacharacters (spaces, quotes, $, ;, |, &, >, <) are not allowed."
        )


def _require_walltime(value: int) -> None:
    """Assert ``value`` is within the permitted walltime range.

    Args:
        value: Walltime in seconds.

    Raises:
        TaskInputError: If ``value`` is outside ``[_MIN_WALLTIME_S, _MAX_WALLTIME_S]``.
    """
    if not (_MIN_WALLTIME_S <= value <= _MAX_WALLTIME_S):
        raise TaskInputError(
            f"walltime_s {value} is outside the permitted range "
            f"[{_MIN_WALLTIME_S}, {_MAX_WALLTIME_S}] seconds."
        )


def _require_nodes(value: int) -> None:
    """Assert ``value`` is within the permitted node count range.

    Args:
        value: Number of compute nodes.

    Raises:
        TaskInputError: If ``value`` is outside ``[_MIN_NODES, _MAX_NODES]``.
    """
    if not (_MIN_NODES <= value <= _MAX_NODES):
        raise TaskInputError(
            f"nodes {value} is outside the permitted range "
            f"[{_MIN_NODES}, {_MAX_NODES}]."
        )


# ---------------------------------------------------------------------------
# Data model — immutable value object; validates all fields at construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    """Immutable descriptor for a single workflow task node.

    ``Task`` is the trust boundary for externally-sourced data.  All fields
    are validated in ``__post_init__`` against allowlists before the object
    is admitted to the domain.  Once constructed, a ``Task`` is guaranteed
    to contain only safe, well-formed values.

    ``frozen=True`` enforces value-object semantics: constructed once, never
    mutated.  ``tuple`` for ``depends_on`` for the same reason.

    Args:
        name: Unique task identifier.  Must match ``_NAME_PATTERN``.
        script: Path to the executable script or binary.  Must match
            ``_SCRIPT_PATH_PATTERN`` — no shell metacharacters permitted.
        depends_on: Names of upstream tasks.  Each entry must match
            ``_NAME_PATTERN``.
        walltime_s: Wall-clock time limit in seconds.  Must be in
            ``[1, 604_800]``.  Default 1800 (30 min).
        nodes: Number of compute nodes to request.  Must be in
            ``[1, 100_000]``.  Default 1.
        mpi: Whether MPI parallelism is required.  Default False.

    Raises:
        TaskInputError: If any field fails allowlist or bounds validation.
    """

    name: str
    script: str
    depends_on: tuple[str, ...] = ()
    walltime_s: int = 1800
    nodes: int = 1
    mpi: bool = False

    def __post_init__(self) -> None:
        """Validate all fields at the trust boundary."""
        _require_name(self.name, "Task name")
        _require_script_path(self.script)
        for dep in self.depends_on:
            _require_name(dep, "Dependency name")
        _require_walltime(self.walltime_s)
        _require_nodes(self.nodes)


# ---------------------------------------------------------------------------
# Result type — named tuple keeps the critical-path return value readable
# ---------------------------------------------------------------------------


class CriticalPath(NamedTuple):
    """Result of a critical-path analysis.

    Attributes:
        tasks: Ordered list of task names on the critical path.
        duration_s: Total wall-clock seconds along that path.
    """

    tasks: list[str]
    duration_s: int

    @property
    def duration_hm(self) -> str:
        """Human-readable duration as ``HHh MMm``."""
        return f"{self.duration_s // 3600:02d}h {(self.duration_s % 3600) // 60:02d}m"


# ---------------------------------------------------------------------------
# Graph — structure, validation, ordering, and analysis only
# ---------------------------------------------------------------------------


@dataclass
class WorkflowGraph:
    """Validated workflow DAG backed by graphlib.TopologicalSorter.

    Composes a graphlib-compatible adjacency dict internally.  Does not
    extend ``TopologicalSorter`` — it *uses* one, freshly constructed per
    operation to keep each call stateless and independently repeatable.

    All ``Task`` objects admitted here have already passed trust-boundary
    validation in ``Task.__post_init__``.  This class performs only
    structural validation: duplicate names, unknown dependencies, cycles.

    Responsibilities:
        - Task registration
        - Structural validation (duplicates, unknown dependencies, cycles)
        - Topological ordering
        - Parallel execution wave grouping
        - Critical-path analysis by walltime

    Example::

        graph = WorkflowGraph()
        graph.add_task(Task("prep", "prep.sh"))
        graph.add_task(Task("run",  "run.sh",  depends_on=("prep",)))
        graph.validate()
        print(graph.topological_order())   # ['prep', 'run']
    """

    _tasks: dict[str, Task] = field(default_factory=dict, init=False, repr=False)
    _adjacency: dict[str, set[str]] = field(
        default_factory=dict, init=False, repr=False
    )

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_task(self, task: Task) -> None:
        """Register a task and its declared dependencies.

        Args:
            task: A validated ``Task`` instance.  Must have a unique ``name``.

        Raises:
            WorkflowValidationError: If a task with the same name already exists.
        """
        if task.name in self._tasks:
            raise WorkflowValidationError(f"Duplicate task name: '{task.name}'")
        self._tasks[task.name] = task
        self._adjacency[task.name] = set(task.depends_on)

    # ------------------------------------------------------------------
    # Read-only access
    # ------------------------------------------------------------------

    @property
    def tasks(self) -> dict[str, Task]:
        """Read-only view of registered tasks keyed by name."""
        return self._tasks

    # ------------------------------------------------------------------
    # Structural validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Assert the graph is a valid DAG.

        Checks unknown dependency references first (gives a cleaner
        error message than letting graphlib report a missing node), then
        delegates cycle detection to ``graphlib.TopologicalSorter``.

        Raises:
            WorkflowValidationError: If any task depends on an undeclared task.
            WorkflowCycleError: If the dependency graph contains a cycle.
        """
        for name, task in self._tasks.items():
            for dep in task.depends_on:
                if dep not in self._tasks:
                    raise WorkflowValidationError(
                        f"Task '{name}' depends on undeclared task '{dep}'"
                    )

        try:
            ts = graphlib.TopologicalSorter(self._adjacency)
            ts.prepare()
            while ts.is_active():
                ts.done(*ts.get_ready())
        except graphlib.CycleError as exc:
            raise WorkflowCycleError(f"Dependency cycle detected: {exc}") from exc

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    def topological_order(self) -> list[str]:
        """Return one valid linear execution order for all tasks.

        Constructs a fresh ``TopologicalSorter`` on each call so the
        result is always consistent regardless of prior calls.

        Returns:
            Task names in a valid dependency-respecting order.
        """
        return list(graphlib.TopologicalSorter(self._adjacency).static_order())

    def execution_waves(self) -> list[list[str]]:
        """Group tasks into parallel execution waves.

        Wave *N* contains every task whose dependencies are all satisfied
        by waves 0..N-1.  Tasks within a wave may run concurrently.

        Returns:
            List of waves; each wave is a sorted list of task names.
        """
        waves: list[list[str]] = []
        ts = graphlib.TopologicalSorter(self._adjacency)
        ts.prepare()
        while ts.is_active():
            wave = ts.get_ready()
            if not wave:
                break
            waves.append(sorted(wave))
            ts.done(*wave)
        return waves

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def critical_path(self) -> CriticalPath:
        """Compute the critical path by cumulative walltime.

        Uses dynamic programming over the topological order — O(V+E).

        Returns:
            A ``CriticalPath`` named tuple with the path and its
            total duration in seconds.
        """
        dist: dict[str, tuple[int, list[str]]] = {}

        for name in self.topological_order():
            task = self._tasks[name]
            if not task.depends_on:
                dist[name] = (task.walltime_s, [name])
            else:
                best_secs, best_path = max(
                    (dist[dep][0], dist[dep][1]) for dep in task.depends_on
                )
                dist[name] = (best_secs + task.walltime_s, best_path + [name])

        cp_name = max(dist, key=lambda n: dist[n][0])
        return CriticalPath(tasks=dist[cp_name][1], duration_s=dist[cp_name][0])


# ---------------------------------------------------------------------------
# Rendering — visualisation is not a graph concern
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AsciiRenderer:
    """Renders a WorkflowGraph as a human-readable ASCII diagram.

    Task names used in output are guaranteed safe by ``Task.__post_init__``
    validation — no escaping is required at render time.

    Args:
        graph: The workflow graph to render.

    Example::

        renderer = AsciiRenderer(graph)
        print(renderer.render())
    """

    graph: WorkflowGraph

    def render(self) -> str:
        """Produce an ASCII DAG diagram with critical-path annotation.

        Returns:
            Multi-line string suitable for terminal output.
        """
        cp = self.graph.critical_path()
        cp_set = set(cp.tasks)
        rule = "─" * 50

        lines: list[str] = ["Workflow DAG", rule]

        for name in self.graph.topological_order():
            task = self.graph.tasks[name]
            marker = "★" if name in cp_set else "○"
            deps = f"  ← {', '.join(task.depends_on)}" if task.depends_on else ""
            wt = f"{task.walltime_s // 3600:02d}:{(task.walltime_s % 3600) // 60:02d}h"
            resources = f"  [{task.nodes}N{' MPI' if task.mpi else ''} {wt}]"
            lines.append(f"  {marker} {name}{deps}{resources}")

        lines += [
            rule,
            f"  Critical path : {' → '.join(cp.tasks)}",
            f"  Wall-clock est: {cp.duration_hm}",
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class DotExporter:
    """Exports a WorkflowGraph to Graphviz DOT format.

    Critical-path nodes and edges are highlighted in red.

    DOT injection safety: task names are placed inside DOT double-quoted
    identifiers (``"name"``).  ``_NAME_PATTERN`` permits only alphanumerics
    and underscores — it excludes backslash and double-quote — so no name
    admitted by ``Task.__post_init__`` can escape the DOT string context.
    No additional escaping is needed, but the guarantee is only valid while
    ``_NAME_PATTERN`` remains restricted to ``[a-zA-Z0-9_]``.

    Args:
        graph: The workflow graph to export.

    Example::

        exporter = DotExporter(graph)
        Path("dag.dot").write_text(exporter.export())
        # dot -Tsvg dag.dot -o dag.svg
    """

    graph: WorkflowGraph

    def export(self) -> str:
        """Produce a Graphviz DOT representation of the graph.

        Returns:
            DOT-format string, ready to pipe to ``dot -Tsvg``.
        """
        cp_set = set(self.graph.critical_path().tasks)

        lines = [
            "digraph workflow {",
            "  rankdir=LR;",
            '  node [shape=box fontname="monospace"];',
        ]

        for name in self.graph.tasks:
            colour = "red" if name in cp_set else "black"
            lines.append(f'  "{name}" [color={colour}];')

        for name, task in self.graph.tasks.items():
            for dep in task.depends_on:
                on_cp = name in cp_set and dep in cp_set
                attrs = " [color=red penwidth=2]" if on_cp else ""
                lines.append(f'  "{dep}" -> "{name}"{attrs};')

        lines.append("}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Example factory — NWP cycle
# ---------------------------------------------------------------------------


def _build_nwp_example() -> WorkflowGraph:
    """Build a representative NWP forecast cycle graph for demonstration.

    Returns:
        A validated WorkflowGraph modelling a 7-task NWP cycle.
    """
    graph = WorkflowGraph()
    graph.add_task(Task("prep_obs", "scripts/prep_obs.sh", walltime_s=1800, nodes=4))
    graph.add_task(Task("prep_bkg", "scripts/prep_bkg.sh", walltime_s=900, nodes=2))
    graph.add_task(
        Task(
            "enkf",
            "scripts/enkf.py",
            depends_on=("prep_obs", "prep_bkg"),
            walltime_s=3600,
            nodes=80,
            mpi=True,
        )
    )
    graph.add_task(
        Task(
            "post_enkf",
            "scripts/post_enkf.sh",
            depends_on=("enkf",),
            walltime_s=600,
            nodes=2,
        )
    )
    graph.add_task(
        Task(
            "forecast",
            "bin/forecast.x",
            depends_on=("enkf",),
            walltime_s=7200,
            nodes=240,
            mpi=True,
        )
    )
    graph.add_task(
        Task(
            "post_proc",
            "scripts/post.sh",
            depends_on=("forecast",),
            walltime_s=2700,
            nodes=8,
        )
    )
    graph.add_task(
        Task(
            "verification",
            "scripts/verify.py",
            depends_on=("post_enkf", "post_proc"),
            walltime_s=900,
            nodes=4,
        )
    )
    graph.validate()
    return graph


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Demonstrate the DAG engine: rendering, waves, cycle detection, and
    trust-boundary rejection of malicious inputs."""
    graph = _build_nwp_example()

    print(AsciiRenderer(graph).render())

    print("\n── Parallel Execution Waves ─────────────────────")
    for i, wave in enumerate(graph.execution_waves()):
        print(f"  Wave {i}: {wave}")

    print("\n── Cycle Detection ──────────────────────────────")
    cyclic = WorkflowGraph()
    cyclic.add_task(Task("a", "a.sh", depends_on=("c",)))
    cyclic.add_task(Task("b", "b.sh", depends_on=("a",)))
    cyclic.add_task(Task("c", "c.sh", depends_on=("b",)))
    try:
        cyclic.validate()
    except WorkflowCycleError as exc:
        print(f"  ✓ Caught cycle: {exc}")

    print("\n── Trust Boundary — Injection Attempts Rejected ─")
    _demo_rejection("name with spaces", "task a", "run.sh")
    _demo_rejection("shell metachar $", "task_$USER", "run.sh")
    _demo_rejection("DOT injection", 'bad"; color=red; //', "run.sh")
    _demo_rejection("shell in script", "task_x", "run.sh; rm -rf /")
    _demo_rejection("negative walltime", "task_y", "run.sh", walltime_s=-1)
    _demo_rejection("zero nodes", "task_z", "run.sh", nodes=0)

    print("\n── Graphviz DOT (pipe to: dot -Tsvg) ───────────")
    print(DotExporter(graph).export())


def _demo_rejection(label: str, name: str, script: str, **kwargs: object) -> None:
    """Attempt to construct an invalid Task and confirm rejection.

    Args:
        label:  Human-readable description of the attack vector.
        name:   Task name to attempt.
        script: Script path to attempt.
        **kwargs: Additional Task fields forwarded verbatim.
    """
    try:
        Task(name, script, **kwargs)  # type: ignore[arg-type]
        print(f"  FAIL — {label!r} was not rejected")
    except TaskInputError as exc:
        print(f"  ✓ Rejected {label!r}: {exc}")


if __name__ == "__main__":
    main()
