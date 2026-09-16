# Build output safety audit — 2026-09-16

`scripts/build_graph.py` is now fail-closed around the frozen derived graph:

- `--out-dir` is mandatory, so an accidental default invocation cannot write
  into the protected graph.
- Any output path equal to or below `data/derived/graph/` is rejected before
  raw data is opened.
- The explicit protected-path test exited with code `2` and reported the
  refusal. `--help` still works without reading data.

Only the output-path guard is part of this audit. Existing uncommitted builder
work remains preserved separately in the worktree.
