# Track 7 — continual learning / architecture queue

Status: `QUEUED_2VCPU`.

Question: can a small, reproducible continual-learning or architecture
smoke be evaluated on this 2-vCPU / 15-GiB / CPU-only host without claiming
that the full 165122-neuron connectome was powered?

Prerequisites: a frozen task and split, a positive control, independent
train/test liveness and rate gates, a no-network baseline, an explicit
compute budget, and a declared small-subgraph or model budget. Any later run
must receive a new protocol and result directory before metrics are seen.

No execution or measurement is claimed here. This queue marker is not a
memory, topology, architecture, biological, or profitability result. The
current handoff authorizes no new scientific ID after the single
`EXP-IGNITE-002` branch; this document records the bounded next track only.
