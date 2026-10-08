# STATUS_BEFORE_ANOMALY — Fly Lab (pre Anomaly Detector V1)

**Generated:** 2026-09-15 (inspection only; no data deleted)  
**Host:** Ubuntu-1 Lightsail eu-central-1 · 2 vCPU · 15 GiB RAM · ~150 GiB free · **no jobs running**  
**Git tip:** `fe089d3` (main, clean except untracked results/docs + dirty `PROJECT_STATE.json`)

---

## 1. Processes / standby

- **None.** No Python fly-lab jobs. Load ~0. User previously paused work.
- Agents in the group chat had claimed: data/E0, polarity, sparse graph, dynamics, E1 harness, null ensemble, portfolio brief. All idle.

## 2. Recent commits (newest first)

| Commit | What |
|---|---|
| `fe089d3` | PROTOCOL ablations lib: weight permutation + top-k hubs |
| `7a5e3d2` / `21d7fad` | `build_graph.py` restored; polarity ground_truth preference |
| `5b796db` | E1 audit fixes report / handoff |
| `13bb88e`…`25cf1bc` | null ensemble, matched MLP, PC gate, spectral gain, leak fix |
| `ad1d670` | Pre-fix broken harness preserved |

## 3. Datasets (frozen)

`data/raw/malecns_v1/` — MaleCNS **v1.0** feathers, SHA-256 verified earlier:

- connectome-weights (~1003 MB)
- body-annotations (~14 MB)
- body-neurotransmitters (~42 MB)

**Do not re-download / do not modify `data/raw/`.**

## 4. Frozen graph

From `data/derived/graph/graph_meta.json`:

- Filter: `status==Traced` both ends  
- **|V| = 165,122** · **|E| = 25,563,197** · Σw = 124,025,046  
- Artifacts: `csr_unsigned.npz`, `csc_unsigned.npz`, `coo_signed.npz`, `neurons.feather`

## 5. Work finished

- E0 data + graph + polarity infrastructure  
- E1 instrument audit (leak, liveness, degree-preserving null, PC-A/B, spectral gain)  
- **Powered null ensemble** → connectome does not beat nulls  
- Glu polarity sensitivity arms (acc insensitive; sparsity/ops change)  
- Portfolio brief for Claude  

## 6. Work half-done / blocked

| Item | Status |
|---|---|
| PROTOCOL ablations **runs** (`|w|`, weight-perm, hubs) | Code in `ablations.py` (library only); **no powered result JSON** (`ablations.log` empty) |
| `PROJECT_STATE.json` | Stale (still says paso 2 mid-run) |
| Untracked result JSONs | Present on disk; not all committed |
| Anomaly Detector | **Not started** |

## 7. E1 pending (decision for Anomaly mission)

Powered comparison already exists:

`experiments/results/e1_null_ensemble_powered_20260915T130422Z_fe089d3.json`

- connectome_signed **0.634 ± 0.122**  
- ER **0.651 ± 0.017** · degree-preserving **0.685 ± 0.030**  
- MLP matched **0.642 ± 0.123**  
- Diffs vs nulls: CI includes 0  

**Formal close (Anomaly Phase 1):**  
`E1_TOPOLOGY_ADVANTAGE = FALSE`  

Remaining ablaciones are **not** required to unblock Anomaly V1; skip heavy rescue budget.

## 8. Reusable code

- `flylab/{graph,dynamics,nulls,spectral,polarity}.py`  
- `experiments/harness/{e1_reservoir,null_ensemble,positive_control,gain_sweep,polarity_arms,ablations}.py`  
- `scripts/{build_graph,download_malecns,verify_raw_sha256}.py`  
- Tests under `tests/` · PROTOCOL in `experiments/PROTOCOL.md` · audit in `reports/E1_audit_fixes.md`

## 9. Results inventory (high signal)

- **Valid powered E1:** `e1_null_ensemble_powered_*_fe089d3.json`  
- **PC pass:** `e1_positive_control_20260915T122911Z_3bd93f0.json`  
- **Polarity:** `e1_polarity_arms_*_fe089d3.json`  
- **Invalid / legacy:** `e1_pilot.json` and pre-fix files (see results README)

## 10. Next steps (post this file)

1. Record `E1_TOPOLOGY_ADVANTAGE=FALSE`  
2. Scaffold Anomaly Detector V1 (synthetic temporal signals → encoder → MaleCNS subgraph → score)  
3. Baselines + EXP-ANOM-001 smoke  
4. Sensors adapters only after V1 science loop works  

