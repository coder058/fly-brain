# experiments/results

## Naming

Results are written to `<prefix>_<UTC timestamp>_<git rev>.json` by
`experiments/harness/e1_reservoir.write_result`. Nothing here is ever overwritten;
if a name somehow collides a numeric suffix is appended. Every file carries a
`provenance` block (UTC time, git rev, SHA-256 of the harness source and of the
config that produced it).

## Legacy files (pre-fix, kept for the record — do not delete)

These predate the audit fixes and are **not valid results**. They were produced by
a harness that read out driven input neurons directly, so their accuracies measure
label leakage, not computation. See `reports/E1_audit_fixes.md`.

- `e1_pilot.json` — final surviving state of a file that was overwritten in place on
  every run, so the v1–v6 history it once held is unrecoverable. Its `config.task_hardening`
  field reads `shared_inputs_temporal_phase_only_v2` because the harness stamped that
  string over the config at write time; the config on disk said
  `temporal_hold out_noise055_5class_v6`. Treat the recorded config as untrustworthy.
- `e1_run.log`, `e1_v6.log` — stdout captures from those runs.
