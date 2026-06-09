"""
Simple CLI.
"""

from __future__ import annotations

import argparse


def main() -> None:
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug info",
    )
    subparsers = parser.add_subparsers(dest="command")
    build = subparsers.add_parser("build", help="Build")
    build.add_argument(
        "--template",
        help="read template",
        required=True,
        type=str,
    )
    build.add_argument(
        "--out",
        help="output file",
        required=True,
        type=str,
    )
    build.add_argument(
        "--interactive",
        help="read template",
        required=True,
        type=str,
    )

    comp = subparsers.add_parser("compile", help="Compile")
    comp.add_argument(
        "--config",
        help="read config",
        required=True,
        type=str,
    )
    comp.add_argument(
        "--backend",
        choices=["rocoto", "ecflow"],
        help="target backend",
        required=True,
    )
    comp.add_argument(
        "--out",
        help="output file",
        required=True,
        type=str,
    )

    inspect = subparsers.add_parser("inspect", help="Inspect")
    inspect.add_argument(
        "--config",
        help="read config",
        required=True,
        type=str,
    )
    inspect.add_argument(
        "--format",
        help="target backend",
    )

    lint = subparsers.add_parser("lint", help="Lint")
    lint.add_argument(
        "--config",
        help="read config",
        required=True,
        type=str,
    )
    lint.add_argument(
        "--lang",
        choices=("python", "fortran", "bash"),
        help="target backend",
    )

    validate = subparsers.add_parser("validate", help="Validate")
    validate.add_argument(
        "--config",
        help="read config",
        required=True,
        type=str,
    )
    validate.add_argument(
        "--template",
        help="read template",
        required=True,
        type=str,
    )

    args = parser.parse_args()
    args.func(args)
