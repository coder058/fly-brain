"""Independently check corrected block controls and paired full-run summaries."""

import argparse
import importlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from research import routing_003 as routing  # noqa: E402
from research.motif_func_003 import weighted_edges  # noqa: E402


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    metadata = load_json(run_dir / "metadata.json")
    summary = load_json(run_dir / "summary.json")
    experiment = metadata["experiment"]
    experiment_id = experiment.rsplit("-", 1)[-1]
    # SOURCE: the four frozen MOTIF-FUNC protocols affected by the mapping repair.
    require(experiment_id in ("003", "004", "005", "006"), "unexpected experiment")
    require(metadata["mode"] == "full" and summary["mode"] == "full", "not a full run")
    require(run_dir.name.startswith("FULL_"), "run directory is not full")

    runner_path = root / "research" / f"motif_func_{experiment_id}.py"
    protocol_path = root / "research" / f"{experiment}-PROTOCOL.md"
    require(metadata["runner_sha256"] == routing.sha256_file(runner_path), "runner hash mismatch")
    require(metadata["protocol_sha256"] == routing.sha256_file(protocol_path), "protocol hash mismatch")
    require(run_dir.name.endswith(metadata["git_tip"][:12]), "revision mismatch")

    graph = routing.load_graph(load_neurons=False)
    selected, _ = routing.choose_nodes(graph)
    labels = routing.load_superclasses()
    source, destination, weights = weighted_edges(graph, selected)
    require(metadata["selected_nodes"] == selected.tolist(), "selected nodes mismatch")
    require(metadata["source_edge_records"] == len(source), "edge count mismatch")
    local_labels = labels[selected]
    blocks = defaultdict(list)
    for index, (a, b) in enumerate(zip(source, destination)):
        blocks[(str(local_labels[int(a)]), str(local_labels[int(b)]))].append(index)

    runner = importlib.import_module(f"research.motif_func_{experiment_id}")
    builder = getattr(runner, {
        "003": "weighted_block_null",
        "004": "sign_block_null",
        "005": "magnitude_block_null",
        "006": "magnitude_block_null",
    }[experiment_id])
    arm_name = {
        "003": "block_weight_permuted",
        "004": "block_sign_permuted",
        "005": "block_magnitude_permuted",
        "006": "block_magnitude_permuted",
    }[experiment_id]

    rows = []
    paired = []
    for seed in routing.SEEDS:
        row = load_json(run_dir / f"seed-{seed:02d}.json")
        require(row["seed"] == seed, "seed mismatch")
        require(row["positive_control_pass"], "positive control failed")
        matrix, _, out_source, out_destination, permuted = builder(
            source, destination, weights, labels, selected, seed
        )
        require(matrix.shape == (len(selected), len(selected)), "matrix shape mismatch")
        require(np.array_equal(out_source, source), "source coordinates changed")
        require(np.array_equal(out_destination, destination), "destination coordinates changed")
        require(np.array_equal(weights == 0, permuted == 0), "zero positions changed")
        for indices in blocks.values():
            original_block = weights[indices]
            permuted_block = permuted[indices]
            if experiment_id == "003":
                require(np.array_equal(np.sort(original_block), np.sort(permuted_block)),
                        "weight multiset changed in a true superclass block")
            elif experiment_id == "004":
                require(np.array_equal(np.abs(original_block), np.abs(permuted_block)),
                        "edge magnitude changed in sign control")
                require(np.array_equal(np.sort(np.sign(original_block)),
                                       np.sort(np.sign(permuted_block))),
                        "sign multiset changed in a true superclass block")
            else:
                require(np.array_equal(np.sign(original_block), np.sign(permuted_block)),
                        "edge sign changed in magnitude control")
                require(np.array_equal(np.sort(np.abs(original_block)),
                                       np.sort(np.abs(permuted_block))),
                        "magnitude multiset changed in a true superclass block")

        observed = row["arms"].get("observed_signed", {})
        controlled = row["arms"].get(arm_name, {})
        for arm in (observed, controlled):
            if arm.get("status") == "MEASURED":
                liveness = arm.get("liveness", {})
                require(liveness.get("train", {}).get("alive") is True, "train liveness failed")
                require(liveness.get("test", {}).get("alive") is True, "test liveness failed")
        if observed.get("status") == controlled.get("status") == "MEASURED":
            paired.append(observed["metrics"]["routing_margin"]
                          - controlled["metrics"]["routing_margin"])
        rows.append(row)

    reported = summary["aggregate"]["paired_primary"]
    require(reported["n"] == len(paired), "paired count mismatch")
    require(reported["values"] == paired, "paired values mismatch")
    if paired:
        require(reported["mean"] == float(np.mean(paired)), "paired mean mismatch")
    if len(paired) > 1:
        # SOURCE: frozen protocol requires a 95% Student-t interval over paired seeds.
        half = float(student_t.ppf(0.975, len(paired) - 1)
                     * np.std(paired, ddof=1) / np.sqrt(len(paired)))
        mean = float(np.mean(paired))
        require(reported["ci95"] == [mean - half, mean + half], "paired interval mismatch")

    audit = {
        "experiment": experiment,
        "classification": "AUDIT_PASSED_ENGINEERING_ONLY",
        "run_dir": str(run_dir.relative_to(root)),
        "run_summary_sha256": routing.sha256_file(run_dir / "summary.json"),
        "runner_sha256": metadata["runner_sha256"],
        "protocol_sha256": metadata["protocol_sha256"],
        "git_tip": metadata["git_tip"],
        "selected_nodes": len(selected),
        "edge_records": len(source),
        "true_superclass_blocks": len(blocks),
        "seeds_checked": len(rows),
        "paired_measured": len(paired),
        "checks": ["global-to-local labels", "block multiset", "zero positions",
                   "fixed edge coordinates", "train/test liveness", "paired arithmetic",
                   "source and protocol hashes"],
        "scope": "corrected post-result functional rerun; not independent confirmation or biology",
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = root / "research" / "results" / experiment / f"AUDIT_REPAIR_{stamp}_{routing.git_rev()[:12]}"
    outdir.mkdir(parents=True, exist_ok=False)
    routing.write_json_once(outdir / "summary.json", audit)
    print(json.dumps(audit, indent=2, sort_keys=True))
    print("WROTE", outdir / "summary.json")


if __name__ == "__main__":
    main()
