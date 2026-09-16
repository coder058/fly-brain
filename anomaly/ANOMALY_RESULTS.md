# Anomaly Detector V1 — Results log

Updated: 2026-09-15T19:08:52.825281+00:00

## EXP-ANOM-001 (`exp_anom_001_20260915T190351Z.json`)
- ceiling_like: None
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 1.000 | 1.000 |
| pca | 1.000 | 1.000 |
| isolation_forest | 0.968 | 0.966 |
| ocsvm | 1.000 | 1.000 |
| mlp_recon | 1.000 | 1.000 |
| fly_signed | 0.978 | 0.970 |
| fly_er_null | 0.949 | 0.951 |
| fly_abs | 1.000 | 1.000 |

## EXP-ANOM-002 (`exp_anom_002_20260915T190454Z.json`)
- ceiling_like: False
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 0.712 | 0.725 |
| pca | 0.684 | 0.615 |
| isolation_forest | 0.514 | 0.484 |
| ocsvm | 0.633 | 0.575 |
| mlp_recon | 0.701 | 0.627 |
| fly_signed | 0.519 | 0.486 |
| fly_er_null | 0.483 | 0.479 |
| fly_abs | 0.577 | 0.550 |

## EXP-ANOM-003 (`exp_anom_003_20260915T190502Z.json`)
- ceiling_like: False
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 0.971 | 0.880 |
| pca | 1.000 | 1.000 |
| isolation_forest | 1.000 | 1.000 |
| ocsvm | 1.000 | 1.000 |
| mlp_recon | 1.000 | 1.000 |
| fly_signed | 0.575 | 0.180 |
| fly_er_null | 0.461 | 0.128 |
| fly_abs | 0.885 | 0.431 |

## EXP-ANOM-004 (`exp_anom_004_20260915T190657Z.json`)
- ceiling_like: False
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 0.975 | 0.975 |
| pca | 0.835 | 0.828 |
| isolation_forest | 0.571 | 0.513 |
| ocsvm | 0.845 | 0.829 |
| mlp_recon | 0.810 | 0.819 |
| fly_signed | 0.532 | 0.497 |
| fly_er_null | 0.617 | 0.588 |
| fly_abs | 0.589 | 0.620 |

## EXP-ANOM-004 (`exp_anom_004_20260915T190703Z.json`)
- ceiling_like: False
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 0.652 | 0.586 |
| pca | 0.547 | 0.554 |
| isolation_forest | 0.556 | 0.497 |
| ocsvm | 0.537 | 0.545 |
| mlp_recon | 0.582 | 0.589 |
| fly_signed | 0.422 | 0.412 |
| fly_er_null | 0.504 | 0.482 |
| fly_abs | 0.537 | 0.491 |

## EXP-ANOM-004 (`exp_anom_004_20260915T190709Z.json`)
- ceiling_like: False
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 0.567 | 0.484 |
| pca | 0.496 | 0.513 |
| isolation_forest | 0.547 | 0.478 |
| ocsvm | 0.489 | 0.506 |
| mlp_recon | 0.539 | 0.553 |
| fly_signed | 0.511 | 0.457 |
| fly_er_null | 0.478 | 0.488 |
| fly_abs | 0.453 | 0.437 |

## EXP-ANOM-004 (`exp_anom_004_20260915T190715Z.json`)
- ceiling_like: False
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 0.553 | 0.471 |
| pca | 0.479 | 0.500 |
| isolation_forest | 0.543 | 0.475 |
| ocsvm | 0.465 | 0.487 |
| mlp_recon | 0.527 | 0.540 |
| fly_signed | 0.452 | 0.431 |
| fly_er_null | 0.587 | 0.562 |
| fly_abs | 0.424 | 0.397 |

## EXP-ANOM-005 (`exp_anom_005_20260915T190723Z.json`)
- ceiling_like: False
| arm | AUROC | AUPRC |
|---|---|---|
| threshold | 0.793 | 0.748 |
| pca | 0.683 | 0.557 |
| isolation_forest | 0.689 | 0.564 |
| ocsvm | 0.661 | 0.538 |
| mlp_recon | 0.662 | 0.539 |
| fly_signed | 0.497 | 0.395 |
| fly_er_null | 0.479 | 0.472 |
| fly_abs | 0.475 | 0.419 |

## EXP-ANOM-006 (`exp_anom_006_20260915T190852Z.json`)
| arm | mean AUROC ± CI95 |
|---|---|
| threshold | 0.733 ± 0.017 |
| pca | 0.658 ± 0.032 |
| fly_signed | 0.519 ± 0.027 |
| fly_abs | 0.514 ± 0.022 |
| er_null | 0.534 ± 0.030 |
| weight_perm | 0.527 ± 0.033 |
| hubs_removed | 0.519 ± 0.027 |
- verdict: `{'beats_er_null': False, 'beats_weight_perm': False, 'beats_threshold_baseline': False, 'diff_vs_er': -0.014513888888888937, 'diff_vs_weight_perm': -0.008319444444444435, 'diff_vs_threshold': -0.21391666666666653, 'ANOMALY_TOPOLOGY_ADVANTAGE': False}`

