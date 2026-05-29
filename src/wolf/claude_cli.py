"""WOLF command-line interface.

All commands are stateless: read inputs, produce outputs, exit.
No daemons, no lock files, no database.

Rings in use per command:
    wolf validate      Ring 1.5 (jsonschema) or Ring 1 (regex fallback)
    wolf compile       Ring 1   (pure text generation)
    wolf inspect       Ring 1   (graphlib) or Ring 2 (networkx)
    wolf lint          Ring 1.5 (external linter binaries via subprocess)
    wolf capabilities  Ring 1   (shutil.which + importlib.util.find_spec only)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CLI framework — argparse (Ring 1) only
# Click is Ring 2; we avoid it here so the CLI is available everywhere.
# ---------------------------------------------------------------------------


def _base_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wolf",
        description="WOLF — Workflow Orchestration Layer Fabric",
    )
    p.add_argument("--version", action="version", version=_wolf_version())
    return p


def main(argv: list[str] | None = None) -> None:
    """WOLF CLI entry point."""
    parser = _base_parser()
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # wolf validate
    p_val = sub.add_parser("validate", help="Validate a WOLF YAML config")
    p_val.add_argument("-c", "--config", required=True, type=Path)
    p_val.add_argument("--strict", action="store_true")
    p_val.add_argument("--report", choices=["text", "json"], default="text")
    p_val.add_argument(
        "-v", "--var", action="append", default=[], metavar="KEY=VALUE")

    # wolf compile
    p_cmp = sub.add_parser(
        "compile", help="Compile YAML to backend definition files")
    p_cmp.add_argument("-c", "--config", required=True, type=Path)
    p_cmp.add_argument("-b", "--backend", default=None)
    p_cmp.add_argument("-o", "--out", type=Path, default=Path("./wolf_out"))
    p_cmp.add_argument(
        "-v", "--var", action="append", default=[], metavar="KEY=VALUE")

    # wolf inspect
    p_ins = sub.add_parser("inspect", help="Visualise the workflow DAG")
    p_ins.add_argument("-c", "--config", required=True, type=Path)
    p_ins.add_argument("--format", choices=["ascii", "dot"], default="ascii")
    p_ins.add_argument("--critical-path", action="store_true")
    p_ins.add_argument(
        "-v", "--var", action="append", default=[], metavar="KEY=VALUE")

    # wolf lint
    p_lnt = sub.add_parser("lint", help="Static analysis on workflow scripts")
    p_lnt.add_argument("-c", "--config", required=True, type=Path)
    p_lnt.add_argument("--lang", default="all")
    p_lnt.add_argument("--report", choices=["text", "json"], default="text")
    p_lnt.add_argument("--script-root", type=Path, default=None)
    p_lnt.add_argument(
        "-v", "--var", action="append", default=[], metavar="KEY=VALUE")

    # wolf capabilities
    p_cap = sub.add_parser(
        "capabilities", help="Probe available backends and ring level")
    p_cap.add_argument("--json", action="store_true", dest="as_json")

    # wolf build
    p_bld = sub.add_parser(
        "build", help="Scaffold a new workflow from a template")
    p_bld.add_argument("-t", "--template", required=True)
    p_bld.add_argument("-b", "--backend", required=True)
    p_bld.add_argument("-o", "--out", type=Path, default=Path("workflow.yaml"))
    p_bld.add_argument("--no-interactive", action="store_true")

    args = parser.parse_args(argv)

    dispatch = {
        "validate":     _cmd_validate,
        "compile":      _cmd_compile,
        "inspect":      _cmd_inspect,
        "lint":         _cmd_lint,
        "capabilities": _cmd_capabilities,
        "build":        _cmd_build,
    }

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except KeyboardInterrupt:
        sys.exit(130)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_validate(args: argparse.Namespace) -> None:
    from wolf.schema import WorkflowConfig
    from wolf.adapters import get_compiler

    extra = _parse_vars(args.var)
    try:
        cfg = WorkflowConfig.from_yaml(args.config, extra)
        graph = cfg.build_graph()
        compiler = get_compiler(cfg.backend)
        warnings = compiler.validate_constraints(graph, cfg)
    except Exception as exc:
        _emit({"status": "FAIL", "errors": [str(exc)]}, args.report)
        sys.exit(1)

    result: dict[str, Any] = {
        "status": "WARN" if warnings else "OK",
        "workflow": cfg.meta.name,
        "backend": cfg.backend,
        "tasks": len(cfg.tasks),
        "warnings": warnings,
    }
    _emit(result, args.report)
    if args.strict and warnings:
        sys.exit(1)


def _cmd_compile(args: argparse.Namespace) -> None:
    from wolf.schema import WorkflowConfig
    from wolf.adapters import get_compiler

    extra = _parse_vars(args.var)
    cfg = WorkflowConfig.from_yaml(args.config, extra)
    if args.backend:
        # shallow backend override — rebuild meta with different backend
        d = {
            "meta": {**{"name": cfg.meta.name, "backend": args.backend,
                        "version": cfg.meta.version, "owner": cfg.meta.owner}},
            "environment": {
                "modules": cfg.environment.modules,
                "vars": cfg.environment.vars,
                "shell": cfg.environment.shell,
            },
            "workflow": {"tasks": {
                n: {"script": str(t.script), "depends_on": list(t.depends_on),
                    "walltime_s": t.walltime_s, "nodes": t.nodes, "mpi": t.mpi}
                for n, t in cfg.tasks.items()
            }},
        }
        cfg = WorkflowConfig.from_dict(d)

    graph = cfg.build_graph()
    compiler = get_compiler(cfg.backend)
    artefacts = compiler.compile(graph, cfg)

    args.out.mkdir(parents=True, exist_ok=True)
    for rel, content in artefacts.items():
        dest = args.out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        print(f"  wrote  {dest}")

    print(
        f"\n✓ Compiled '{cfg.meta.name}' → {args.out} ({len(artefacts)} files)")


def _cmd_inspect(args: argparse.Namespace) -> None:
    from wolf.schema import WorkflowConfig

    extra = _parse_vars(args.var)
    cfg = WorkflowConfig.from_yaml(args.config, extra)
    graph = cfg.build_graph()

    if args.format == "ascii":
        print(graph.to_ascii())
    elif args.format == "dot":
        print(graph.to_dot())

    if args.critical_path:
        cp = graph.critical_path()
        print(f"\nCritical path ({cp.duration_hm}):  {' → '.join(cp.tasks)}")


def _cmd_lint(args: argparse.Namespace) -> None:
    from wolf.schema import WorkflowConfig
    from wolf.lint.engine import run_lint

    extra = _parse_vars(args.var)
    cfg = WorkflowConfig.from_yaml(args.config, extra)
    languages = None if args.lang == "all" else [args.lang]
    root = args.script_root or args.config.parent
    report = run_lint(cfg, languages=languages, script_root=root)

    if args.report == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_text())

    if not report.passed():
        sys.exit(1)


def _cmd_capabilities(args: argparse.Namespace) -> None:
    from wolf.capabilities import probe_all

    caps = probe_all()

    if args.as_json:
        data = {
            "ring_level": caps.ring_level,
            "dag_engine": caps.dag_engine,
            "backends": {
                bid: {
                    "compile": cap.compile,
                    "cli": cap.cli,
                    "python_api": cap.python_api,
                    "cli_version": cap.cli_version,
                }
                for bid, cap in caps.backends.items()
            },
        }
        print(json.dumps(data, indent=2))
    else:
        print(caps.format_table())


def _cmd_build(args: argparse.Namespace) -> None:
    from wolf.templates.registry import get_template, list_templates

    tmpl = get_template(args.template)
    if tmpl is None:
        print(
            f"Unknown template '{args.template}'. "
            f"Available: {list_templates()}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.no_interactive:
        print(f"Scaffolding '{args.template}' for backend '{args.backend}'\n")
        filled: dict[str, str] = {}
        for var_name, meta in tmpl.required_vars.items():
            default = meta.get("default", "")
            prompt = f"  {var_name} [{meta.get('description', '')}] (default: {default}): "
            value = input(prompt).strip() or default
            filled[var_name] = value
    else:
        filled = {k: v.get("default", "") for k, v in tmpl.required_vars.items()}

    content = tmpl.render(backend=args.backend, vars=filled)
    args.out.write_text(content, encoding="utf-8")
    print(f"\n✓ Written to {args.out}")
    print(f"  Next: wolf validate --config {args.out}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_vars(raw: list[str]) -> dict[str, str]:
    """Parse KEY=VALUE pairs from CLI --var arguments.

    Args:
        raw: List of ``KEY=VALUE`` strings.

    Returns:
        Dict of key → value.
    """
    result: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            _log.warning(
                "Ignoring malformed --var %r (expected KEY=VALUE)", item)
            continue
        k, _, v = item.partition("=")
        result[k.strip()] = v.strip()
    return result


def _emit(data: dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(data, indent=2))
    else:
        status = data.get("status", "")
        icon = {"OK": "✓", "WARN": "⚠", "FAIL": "✗"}.get(status, "·")
        print(f"{icon} Status: {status}")
        for k, v in data.items():
            if k != "status":
                print(f"  {k}: {v}")


def _wolf_version() -> str:
    try:
        from wolf import __version__
        return f"wolf {__version__}"
    except ImportError:
        return "wolf (dev)"
