from __future__ import annotations

import argparse
import sys

from adaptive_tutor.reporting import generate_report
from adaptive_tutor.runner import run_experiment
from adaptive_tutor.triage_training import train_reading_triage_from_args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adaptive-tutor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-experiment", help="Run the full tutoring experiment.")
    run_parser.add_argument("--config", required=True, help="Path to the YAML experiment config.")

    report_parser = subparsers.add_parser(
        "generate-report", help="Regenerate the Markdown report from an existing run directory."
    )
    report_parser.add_argument("--run-dir", required=True, help="Path to an existing run directory.")

    triage_parser = subparsers.add_parser(
        "train-reading-triage",
        help="Train the PyTorch GRU Reading QA judge triage model from run artifacts.",
    )
    triage_parser.add_argument("--runs", nargs="+", required=True, help="Run directories to read.")
    triage_parser.add_argument("--model-path", required=True, help="Output .pt checkpoint path.")
    triage_parser.add_argument("--epochs", type=int, default=80)
    triage_parser.add_argument("--hidden-size", type=int, default=16)
    triage_parser.add_argument("--confidence-threshold", type=float, default=0.90)
    triage_parser.add_argument("--seed", type=int, default=42)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run-experiment":
        run_dir = run_experiment(args.config)
        print(run_dir)
        return 0
    if args.command == "generate-report":
        generate_report(args.run_dir)
        print(args.run_dir)
        return 0
    if args.command == "train-reading-triage":
        metrics = train_reading_triage_from_args(args)
        print(metrics)
        return 0
    parser.error("Unknown command")
    return 1


def run_experiment_entry() -> None:
    raise SystemExit(main(["run-experiment", *sys.argv[1:]]))


def generate_report_entry() -> None:
    raise SystemExit(main(["generate-report", *sys.argv[1:]]))


def train_reading_triage_entry() -> None:
    raise SystemExit(main(["train-reading-triage", *sys.argv[1:]]))
