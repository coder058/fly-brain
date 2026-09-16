# Anomaly Detector V1 — Limitations

- Synthetic windows only. Sensor adapters are stubs (`CameraAdapter`, `IMUAdapter`, …).
- Scoring is **window-level** (no detection latency inside a window).
- Fly reservoir uses a **128-neuron** top-degree subgraph, not the full 165k graph.
- EXP-001 / parts of EXP-003 can hit AUROC≈1.0 for classical baselines — that is **task ease**, not Fly success.
- EXP-002 (subtle glitch) is the first non-ceiling task: Fly ≈ ER null, both below simple threshold/PCA.
- `E1_TOPOLOGY_ADVANTAGE = FALSE` still holds; Anomaly V1 does not reverse it.
- IsolationForest / OCSVM need `sklearn` in the venv.
- Do not cite a visual demo as success.
