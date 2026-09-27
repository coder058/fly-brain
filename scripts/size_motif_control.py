"""Run one full-trial seed as an operational sizing check, never as evidence."""

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from research import routing_003 as routing  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    # SOURCE: the four frozen MOTIF-FUNC protocols affected by the label repair.
    parser.add_argument("experiment", choices=("003", "004", "005", "006"))
    args = parser.parse_args()

    runner = importlib.import_module(f"research.motif_func_{args.experiment}")
    experiment = f"MOTIF-FUNC-{args.experiment}"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = root / "research" / "results" / experiment / f"SIZING_{stamp}_{routing.git_rev()[:12]}"
    outdir.mkdir(parents=True, exist_ok=False)

    graph = routing.load_graph(load_neurons=False)
    selected, degree = routing.choose_nodes(graph)
    labels = routing.load_superclasses()
    streams = routing.choose_streams(selected, degree, labels)
    source, destination, weights = runner.weighted_edges(graph, selected)
    seed = routing.SEEDS[0]
    row = runner.run_seed(
        graph, selected, degree, labels, streams, source, destination, weights,
        seed, routing.N_TRIALS_PER_PATTERN, False, outdir,
    )
    estimate = row["elapsed_seconds"] * len(routing.SEEDS)
    summary = {
        "experiment": experiment,
        "classification": "SIZING_ONLY_NOT_EVIDENCE",
        "git_tip": routing.git_rev(),
        "protocol_sha256": routing.sha256_file(root / "research" / f"{experiment}-PROTOCOL.md"),
        "runner_sha256": routing.sha256_file(root / "research" / f"motif_func_{args.experiment}.py"),
        "seed": seed,
        "one_seed_seconds": row["elapsed_seconds"],
        "estimated_full_seconds": estimate,
        "positive_control_pass": row["positive_control_pass"],
        "arm_statuses": {name: value.get("status") for name, value in row["arms"].items()},
        "estimate_only": True,
    }
    routing.write_json_once(outdir / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("WROTE", outdir / "summary.json")


if __name__ == "__main__":
    main()
