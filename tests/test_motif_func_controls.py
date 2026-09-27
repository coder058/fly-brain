"""SYNTHETIC regression checks for fixed-topology functional controls."""
import numpy as np
import pytest

from research.motif_func_003 import weighted_block_null
from research.motif_func_004 import sign_block_null
from research.motif_func_005 import magnitude_block_null
from research.motif_func_006 import magnitude_block_null as lower_rate_magnitude_block_null


@pytest.mark.parametrize(
    ("null_builder", "control"),
    [
        (sign_block_null, "sign"),
        (magnitude_block_null, "magnitude"),
        (weighted_block_null, "weight"),
        (lower_rate_magnitude_block_null, "magnitude"),
    ],
    ids=["block-sign", "block-magnitude", "block-weight", "lower-rate-block-magnitude"],
)
def test_block_nulls_use_global_labels_and_keep_isolated_selected_nodes(null_builder, control):
    # PLACEHOLDER: synthetic IDs and weights expose local/global label confusion;
    # these numbers are fixtures, not measurements from MaleCNS.
    selected_nodes = np.array([10, 20, 30, 40, 99], dtype=np.int64)
    global_labels = np.full(100, "UNSELECTED", dtype=object)
    global_labels[selected_nodes] = ["A", "A", "B", "B", "ISOLATED"]

    # SYNTHETIC fixture: two reciprocal blocks have uniform signs, so a valid
    # within-block sign permutation cannot move signs between the A and B blocks.
    src = np.array([0, 1, 2, 3], dtype=np.int64)
    dst = np.array([1, 0, 3, 2], dtype=np.int64)
    weights = np.array([1.0, 4.0, -9.0, -16.0], dtype=np.float32)

    W, diagnostics, _, _, permuted = null_builder(
        src, dst, weights, global_labels, selected_nodes, seed=1
    )

    assert W.shape == (len(selected_nodes), len(selected_nodes))
    if control == "sign":
        assert np.array_equal(np.sign(permuted[:2]), np.array([1.0, 1.0]))
        assert np.array_equal(np.sign(permuted[2:]), np.array([-1.0, -1.0]))
    else:
        assert np.array_equal(np.sort(np.abs(permuted[:2])), np.array([1.0, 4.0]))
        assert np.array_equal(np.sort(np.abs(permuted[2:])), np.array([9.0, 16.0]))
    if control == "weight":
        assert diagnostics["block_weight_multisets_preserved"]
    else:
        assert diagnostics["zero_positions_preserved"]
        assert diagnostics["block_sign_multisets_preserved"]
        assert diagnostics["block_absolute_weight_multisets_preserved"]
