# Data

| path | what | tracked |
|---|---|---|
| `manifests/source.lock.json` | URLs and SHA-256 of the three MaleCNS v1.0 raw files | yes |
| `e1_slice/` | the 500-neuron slice every E1 experiment runs on (70 KB) + neuron annotations | yes |
| `derived/neurons/` | per-neuron polarity table used by `flylab.polarity` | yes |
| `raw/malecns_v1/` | raw feathers, 1.1 GB — `python scripts/download_malecns.py` | no |
| `derived/graph/` | full sparse graph, ~250 MB — `python scripts/build_graph.py --out-dir …` | no |

Rebuilding from scratch on a 4-core / 16 GB machine takes about five minutes and
reproduces the recorded totals exactly: 165,122 traced neurons, 25,563,197 directed
connections, 124,025,046 synapses (E 103,718 / I 27,965 / unknown 33,439 neurons).

## Attribution

MaleCNS v1.0 connectome, Janelia FlyEM — https://male-cns.janelia.org/ — licensed
CC-BY 4.0. Files in `e1_slice/` and `derived/neurons/` are subsets of that dataset
(filtered to traced neurons, signed by predicted neurotransmitter) and are
redistributed under the same license.
