"""Polarity policy: the paths must resolve, and glutamate must be an explicit choice."""
import json

import pytest

from flylab import polarity as P


def test_default_paths_exist():
    """Both constants previously pointed at files that do not exist: DEFAULT_ARTIFACT at
    body_polarity.feather (the artifact is body_polarity_traced.feather) and DEFAULT_POLICY
    at a polarity_policy.json that was never written."""
    assert P.DEFAULT_ARTIFACT.exists(), P.DEFAULT_ARTIFACT
    assert P.DEFAULT_POLICY.exists(), P.DEFAULT_POLICY


def test_policy_file_parses_and_matches_the_code_table():
    doc = json.loads(P.DEFAULT_POLICY.read_text())
    assert doc["default"] == P.DEFAULT_POLICY_NAME
    for name, spec in P.POLICIES.items():
        assert set(doc["policies"][name]["excitatory"]) == set(spec["excitatory"])
        assert set(doc["policies"][name]["inhibitory"]) == set(spec["inhibitory"])


def test_glutamate_differs_across_policies():
    assert P.sign_of("glutamate", "glutamate_unknown") == 0
    assert P.sign_of("glutamate", "glutamate_inhibitory") == -1
    assert P.sign_of("glutamate", "glutamate_excitatory") == 1


def test_unknown_is_never_excitatory():
    for pol in P.POLICIES:
        for nt in ("unclear", "dopamine", "octopamine", "serotonin", None, ""):
            assert P.sign_of(nt, pol) <= 0
            assert P.sign_of(nt, pol) == 0


def test_core_assignments_are_policy_independent():
    for pol in P.POLICIES:
        assert P.sign_of("acetylcholine", pol) == 1
        assert P.sign_of("gaba", pol) == -1
        assert P.sign_of("histamine", pol) == -1


def test_classify_nt_is_case_and_whitespace_insensitive():
    assert P.classify_nt("  ACETYLCHOLINE ") == "EXCITATORY"
    assert P.classify_nt("GABA") == "INHIBITORY"


def test_sign_series_matches_scalar_lookup():
    names = ["acetylcholine", "gaba", "glutamate", "unclear", None, "histamine"]
    for pol in P.POLICIES:
        vec = P.sign_series(names, pol).tolist()
        assert vec == [P.sign_of(x, pol) for x in names]


def test_load_policy_falls_back_without_a_file(tmp_path):
    doc = P.load_policy(tmp_path / "nope.json")
    assert doc["default"] == P.DEFAULT_POLICY_NAME
    assert "glutamate_inhibitory" in doc["policies"]
