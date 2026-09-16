#!/usr/bin/env python3
"""Verify MaleCNS raw feathers against source.lock.json — run after sync."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
lock = json.loads((ROOT / "data/manifests/source.lock.json").read_text())
raw = ROOT / "data/raw/malecns_v1"
ok = True
for name, meta in lock["files"].items():
    p = raw / name
    if not p.exists():
        print("MISSING", name); ok = False; continue
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    expect = meta["sha256"]
    status = "OK" if digest == expect else "MISMATCH"
    if status != "OK":
        ok = False
    print(status, name, digest)
sys.exit(0 if ok else 1)
