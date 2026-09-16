"""Simple anomaly baselines on flattened windows (train on normals only)."""
from __future__ import annotations
import numpy as np

def _flat(X):
    return X.reshape(X.shape[0], -1)

def score_threshold(X_train_n, X_test):
    mu = _flat(X_train_n).mean(0)
    sd = _flat(X_train_n).std(0) + 1e-6
    return np.abs((_flat(X_test) - mu) / sd).max(1)

def score_pca(X_train_n, X_test, k: int = 8):
    F = _flat(X_train_n)
    mu = F.mean(0)
    F0 = F - mu
    Ft = _flat(X_test) - mu
    _, _, vt = np.linalg.svd(F0, full_matrices=False)
    k = min(k, vt.shape[0])
    P = vt[:k].T
    recon = (Ft @ P) @ P.T
    return ((Ft - recon) ** 2).mean(1)

def score_isolation_forest(X_train_n, X_test, seed: int = 0):
    from sklearn.ensemble import IsolationForest
    clf = IsolationForest(random_state=seed, n_estimators=100, contamination="auto")
    clf.fit(_flat(X_train_n))
    return -clf.score_samples(_flat(X_test))

def score_ocsvm(X_train_n, X_test):
    from sklearn.svm import OneClassSVM
    clf = OneClassSVM(kernel="rbf", gamma="scale", nu=0.1)
    clf.fit(_flat(X_train_n))
    return -clf.decision_function(_flat(X_test))

def score_mlp_recon(X_train_n, X_test, seed: int = 0, hidden: int = 32, epochs: int = 40):
    """Tiny linear bottleneck autoencoder (numpy), train on normals."""
    rng = np.random.default_rng(seed)
    F = _flat(X_train_n).astype(np.float64)
    Ft = _flat(X_test).astype(np.float64)
    mu, sd = F.mean(0), F.std(0) + 1e-6
    F = (F - mu) / sd
    Ft = (Ft - mu) / sd
    d = F.shape[1]
    h = min(hidden, d)
    W1 = rng.normal(0, 0.1, size=(d, h))
    W2 = rng.normal(0, 0.1, size=(h, d))
    lr = 0.05
    for _ in range(epochs):
        H = np.tanh(F @ W1)
        recon = H @ W2
        err = recon - F
        dW2 = H.T @ err / len(F)
        dH = err @ W2.T * (1 - H ** 2)
        dW1 = F.T @ dH / len(F)
        W1 -= lr * dW1
        W2 -= lr * dW2
    Ht = np.tanh(Ft @ W1)
    return ((Ht @ W2 - Ft) ** 2).mean(1)
