# Fly Lab — loop boundary audit

This is a control audit, not a scientific result.

- Host: Ubuntu-1, 2 vCPU / 15 GiB / no GPU; one science job at a time.
- Protected inputs: `data/raw/` and the original `data/derived/graph/` were not
  modified; `scripts/verify_graph.py` returned `PASS_STRUCTURAL_CHECKS`.
- Immutable instrument: `EXP-INST-001/conclusion.json` remains SHA-256
  `64098d2e52b17fa07cb939d73bb7d32bb8ec8b36537e45c22d18fdfc36c7aff0`.
- Scientific queue: MEM-001/002/003, GLU-001, IGNITE-001 and IGNITE-002
  remain recorded with their stated gates; no closed ID was reopened.
- Testbeds: NAV-001 is `DEFERRED_HARDWARE`, track 7 is `QUEUED_2VCPU`, and
  the A2A hub is a versioned loopback-only bounded prototype.
- Verification: full suite `74 passed`; no science process is running; no
  new scientific ID is authorized by the current handoff.
- Loop state: `ACTIVE_UNTIL_HUMAN_STOP`; this file does not mark the objective
  complete or authorize work outside the declared queue.
