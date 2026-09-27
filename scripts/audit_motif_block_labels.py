"""Read-only audit of archived versus intended motif-control block labels.

Requires the protected derived graph to be available locally. It does not
write to the graph or to historical experiment artifacts.
"""

import sys
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from research import routing_003 as routing  # noqa: E402
from research.motif_func_003 import weighted_edges  # noqa: E402


def main():
    graph = routing.load_graph(load_neurons=False)
    selected, _ = routing.choose_nodes(graph)
    global_labels = routing.load_superclasses()
    source, destination, _ = weighted_edges(graph, selected)
    local_labels = global_labels[selected]

    archived_blocks = [
        (str(global_labels[int(a)]), str(global_labels[int(b)]))
        for a, b in zip(source, destination)
    ]
    intended_blocks = [
        (str(local_labels[int(a)]), str(local_labels[int(b)]))
        for a, b in zip(source, destination)
    ]

    print("selected_nodes", len(selected))
    print("edge_records", len(source))
    print("mismatched_block_assignments", sum(a != b for a, b in zip(archived_blocks, intended_blocks)))
    print("archived_block_count", len(Counter(archived_blocks)))
    print("intended_block_count", len(Counter(intended_blocks)))


if __name__ == "__main__":
    main()
