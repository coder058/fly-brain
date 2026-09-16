"""Anomaly metrics: AUROC/AUPRC/FPR/FNR at best-F1 threshold."""
from __future__ import annotations
import numpy as np

def _ranks(scores, y):
    order = np.argsort(-scores)
    y = y[order]
    return y

def auroc(y, s):
    y = np.asarray(y); s = np.asarray(s)
    pos = s[y == 1]; neg = s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # Mann-Whitney
    correct = 0.0
    for p in pos:
        correct += (neg < p).sum() + 0.5 * (neg == p).sum()
    return float(correct / (len(pos) * len(neg)))

def auprc(y, s):
    y = np.asarray(y); s = np.asarray(s)
    order = np.argsort(-s)
    y = y[order]
    tp = 0
    precisions = []
    npos = (y == 1).sum()
    if npos == 0:
        return float("nan")
    for i, yi in enumerate(y, 1):
        if yi == 1:
            tp += 1
            precisions.append(tp / i)
    return float(np.mean(precisions)) if precisions else 0.0

def fpr_fnr_at_f1(y, s):
    y = np.asarray(y); s = np.asarray(s)
    best = None
    for thr in np.unique(s):
        pred = (s >= thr).astype(int)
        tp = ((pred == 1) & (y == 1)).sum()
        fp = ((pred == 1) & (y == 0)).sum()
        fn = ((pred == 0) & (y == 1)).sum()
        tn = ((pred == 0) & (y == 0)).sum()
        prec = tp / (tp + fp + 1e-9)
        rec = tp / (tp + fn + 1e-9)
        f1 = 2 * prec * rec / (prec + rec + 1e-9)
        fpr = fp / (fp + tn + 1e-9)
        fnr = fn / (fn + tp + 1e-9)
        if best is None or f1 > best[0]:
            best = (f1, float(fpr), float(fnr), float(thr))
    return {"f1": best[0], "fpr": best[1], "fnr": best[2], "threshold": best[3]}

def summarize(y, s):
    out = {"auroc": auroc(y, s), "auprc": auprc(y, s)}
    out.update(fpr_fnr_at_f1(y, s))
    return out
