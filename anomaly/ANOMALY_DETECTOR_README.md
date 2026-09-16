# Fly Brain Anomaly Detector V1

**Mission:** scientifically evaluated anomaly detection using MaleCNS — not a demo.

## Status

- `E1_TOPOLOGY_ADVANTAGE = FALSE` (powered null ensemble; see `docs/E1_TOPOLOGY_ADVANTAGE.md`)
- Anomaly V1: synthetic signals → baselines + Fly reservoir scorer
- Sensor adapters: stubs only (`adapters/`)

## Run EXP-ANOM-001

```bash
cd ~/fly-lab
. .venv/bin/activate
python -m anomaly.experiments.exp_anom_001
# or:
python anomaly/experiments/exp_anom_001.py
```

Results land in `anomaly/results/exp_anom_001_*.json`.

## Rule

If Fly loses to baselines/nulls → document `RESULT=NEGATIVE`. No theatre.

## Experiments
- 001 smoke · 002 subtle · 003 rare · **004 noise sweep** · **005 temporal hold-out**
- Limitations: `ANOMALY_LIMITATIONS.md`
- CLI smoke: `python -m anomaly`
