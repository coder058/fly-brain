#!/usr/bin/env python3
"""Robust MaleCNS v1.0 raw download: resume, retry, SHA-256, atomic rename."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "malecns_v1"
LOCK = ROOT / "data" / "manifests" / "source.lock.json"
CHECKSUM_OUT = ROOT / "data" / "checksums" / "verified_sha256.json"

CHUNK = 8 * 1024 * 1024
RETRIES = 8
TIMEOUT = 120


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def disk_free(path: Path) -> int:
    return shutil.disk_usage(path).free


def download_one(name: str, url: str, expected: str) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    final = RAW / name
    part = RAW / f".{name}.part"

    if final.exists():
        got = sha256_file(final)
        if got == expected:
            print(f"[ok] {name} already verified")
            return {"file": name, "status": "already_ok", "sha256": got, "bytes": final.stat().st_size}
        print(f"[warn] {name} exists but hash mismatch; re-downloading")
        final.unlink()

    # rough size check: need headroom for largest ~1.2GB + others
    if disk_free(RAW) < 2_000_000_000:
        raise RuntimeError(f"Insufficient disk free under {RAW}: {disk_free(RAW)}")

    existing = part.stat().st_size if part.exists() else 0
    headers = {}
    if existing:
        headers["Range"] = f"bytes={existing}-"
        print(f"[resume] {name} from byte {existing}")

    attempt = 0
    while attempt < RETRIES:
        attempt += 1
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                mode = "ab" if existing and resp.status == 206 else "wb"
                if mode == "wb" and part.exists():
                    part.unlink()
                    existing = 0
                written = existing
                with part.open(mode) as out:
                    while True:
                        chunk = resp.read(CHUNK)
                        if not chunk:
                            break
                        out.write(chunk)
                        written += len(chunk)
                        if written % (64 * 1024 * 1024) < CHUNK:
                            print(f"[progress] {name}: {written / 1e6:.1f} MB", flush=True)
            break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"[retry {attempt}/{RETRIES}] {name}: {e}", flush=True)
            time.sleep(min(2 ** attempt, 60))
            existing = part.stat().st_size if part.exists() else 0
            headers = {"Range": f"bytes={existing}-"} if existing else {}
    else:
        raise RuntimeError(f"Failed to download {name} after {RETRIES} retries")

    size = part.stat().st_size
    print(f"[hash] verifying {name} ({size / 1e6:.1f} MB)…", flush=True)
    got = sha256_file(part)
    if got != expected:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch for {name}: got {got}, expected {expected}")

    os.replace(part, final)  # atomic on same filesystem
    print(f"[done] {name} → {final}", flush=True)
    return {"file": name, "status": "downloaded", "sha256": got, "bytes": size}


def main() -> int:
    lock = json.loads(LOCK.read_text())
    results = []
    for name, meta in lock["files"].items():
        results.append(download_one(name, meta["url"], meta["sha256"]))
    CHECKSUM_OUT.write_text(json.dumps({"verified_at": time.time(), "files": results}, indent=2) + "\n")
    print("ALL RAW FILES VERIFIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
