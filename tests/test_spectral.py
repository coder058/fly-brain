"""Gain must be a controlled parameter: same requested gain -> same effective gain,
whatever each graph's raw weight scale happens to be."""
import numpy as np
import pytest
from scipy import sparse

from flylab.spectral import (
    arm_spectrum,
    dominant_eigenvalue,
    effective_gain,
    spectral_radius,
    syn_scale_for_gain,
)


def test_spectral_radius_matches_numpy(toy_csr):
    ref = float(np.max(np.abs(np.linalg.eigvals(toy_csr.toarray().astype(np.float64)))))
    assert spectral_radius(toy_csr) == pytest.approx(ref, rel=1e-9)


def test_spectral_radius_abs_is_upper_bound(toy_csr):
    assert spectral_radius(toy_csr, signed=False) >= spectral_radius(toy_csr) - 1e-9


def test_gain_roundtrip(toy_csr):
    rho = spectral_radius(toy_csr)
    for gain in (0.3, 1.0, 1.5, 8.0):
        ss = syn_scale_for_gain(rho, gain, tau_m=6.0, dt=1.0)
        assert effective_gain(rho, ss, tau_m=6.0, dt=1.0) == pytest.approx(gain, rel=1e-12)


def test_gain_normalisation_equalises_across_weight_scales(toy_csr):
    """A graph scaled 1000x must get a 1000x smaller syn_scale for the same gain."""
    scaled = toy_csr * 1000.0
    g = 1.1
    a = syn_scale_for_gain(spectral_radius(toy_csr), g, tau_m=6.0)
    b = syn_scale_for_gain(spectral_radius(scaled), g, tau_m=6.0)
    assert a / b == pytest.approx(1000.0, rel=1e-6)


def test_dominant_eigenvalue_sign_is_reported():
    """The MaleCNS top-500 subgraph is inhibition-dominated: its dominant eigenvalue is a
    large negative real, so rho=1 is not an excitatory ignition point. The API has to expose
    the sign, not just the modulus."""
    n = 40
    W = -sparse.eye(n, format="csr") * 5.0
    lam = dominant_eigenvalue(W)
    assert lam.real < 0
    assert spectral_radius(W) == pytest.approx(5.0)


def test_arm_spectrum_keys(toy_csr):
    s = arm_spectrum(toy_csr)
    assert {"rho_signed", "rho_abs", "dominant_eigenvalue_real", "nnz"} <= set(s)


def test_syn_scale_rejects_degenerate_graph():
    with pytest.raises(ValueError):
        syn_scale_for_gain(0.0, 1.0, tau_m=6.0)
