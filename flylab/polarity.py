"""Signed connection polarity from MaleCNS neurotransmitter predictions.

Contract for sparse dynamics:
  edge_sign[i] = polarity.sign[body_pre]
  EXCITATORY=+1, INHIBITORY=-1, UNKNOWN=0
Never treat UNKNOWN as excitatory.

Glutamate is a real scientific choice, not a default
---------------------------------------------------
The original map listed only acetylcholine as excitatory and only GABA/histamine as
inhibitory, so glutamate fell through to UNKNOWN and contributed exactly zero current. On
the E1 top-500 subgraph that silently zeroes 14,237 of 23,708 edges (60.05%), which makes
`connectome_signed` a ~40%-edge subsample of the connectome rather than the connectome. It
also inflates the `ops_proxy` energy figure 2.50x, because those zeroed edges are stored as
explicit zeros and still counted as synaptic operations.

In Drosophila glutamate is frequently inhibitory via the GluCl-alpha chloride channel, so
"unknown" is the least defensible of the three options. Rather than pick one silently, the
mapping is a named policy and E1 runs it as an explicit sensitivity arm.

Monoamines (dopamine, octopamine, serotonin) stay UNKNOWN: they are modulatory rather than
fast ionotropic, so a +-1 sign in a current-based LIF model would misrepresent them.
"""
from __future__ import annotations

from pathlib import Path
import json

import pyarrow.feather as feather
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "data/derived/neurons/body_polarity_traced.feather"
DEFAULT_POLICY = ROOT / "data/derived/neurons/polarity_policy.json"

POLICIES: dict[str, dict[str, list[str]]] = {
    # As originally shipped. Kept as the reference arm so results stay comparable.
    "glutamate_unknown": {
        "excitatory": ["acetylcholine"],
        "inhibitory": ["gaba", "histamine"],
    },
    # GluCl-alpha: glutamate gates a chloride channel in Drosophila.
    "glutamate_inhibitory": {
        "excitatory": ["acetylcholine"],
        "inhibitory": ["gaba", "histamine", "glutamate"],
    },
    # Sensitivity bound in the opposite direction.
    "glutamate_excitatory": {
        "excitatory": ["acetylcholine", "glutamate"],
        "inhibitory": ["gaba", "histamine"],
    },
}
DEFAULT_POLICY_NAME = "glutamate_unknown"

# Backwards-compatible module constants for the default policy.
EXCITATORY = set(POLICIES[DEFAULT_POLICY_NAME]["excitatory"])
INHIBITORY = set(POLICIES[DEFAULT_POLICY_NAME]["inhibitory"])
SIGN = {"EXCITATORY": 1, "INHIBITORY": -1, "UNKNOWN": 0}


def load_policy(path: Path = DEFAULT_POLICY) -> dict:
    """Read the on-disk policy file, falling back to the in-code POLICIES table."""
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {"default": DEFAULT_POLICY_NAME, "policies": POLICIES,
            "source": "flylab.polarity.POLICIES (no policy file on disk)"}


def load_body_polarity(path: Path = DEFAULT_ARTIFACT) -> pd.DataFrame:
    return feather.read_table(path).to_pandas()


def polarity_lookup(df: pd.DataFrame | None = None) -> dict[int, int]:
    """body_id → sign (+1/-1/0)."""
    if df is None:
        df = load_body_polarity()
    return dict(zip(df["body_id"].tolist(), df["sign"].astype(int).tolist()))


def classify_nt(nt_name: str, policy: str | dict = DEFAULT_POLICY_NAME) -> str:
    """Map a neurotransmitter name to EXCITATORY / INHIBITORY / UNKNOWN under `policy`."""
    spec = POLICIES[policy] if isinstance(policy, str) else policy
    n = (nt_name or "unclear").strip().lower()
    if n in {x.lower() for x in spec["excitatory"]}:
        return "EXCITATORY"
    if n in {x.lower() for x in spec["inhibitory"]}:
        return "INHIBITORY"
    return "UNKNOWN"


def sign_of(nt_name: str, policy: str | dict = DEFAULT_POLICY_NAME) -> int:
    return SIGN[classify_nt(nt_name, policy)]


def sign_series(nt_names, policy: str | dict = DEFAULT_POLICY_NAME):
    """Vectorised sign lookup over an iterable of neurotransmitter names."""
    spec = POLICIES[policy] if isinstance(policy, str) else policy
    exc = {x.lower() for x in spec["excitatory"]}
    inh = {x.lower() for x in spec["inhibitory"]}
    s = pd.Series(nt_names, dtype="object").fillna("unclear").astype(str).str.strip().str.lower()
    return s.map(lambda n: 1 if n in exc else (-1 if n in inh else 0)).astype("int8")
