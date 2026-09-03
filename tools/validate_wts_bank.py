#!/usr/bin/env python3
"""Validate an offline WTS bank against a reference prompt layout.

This tool reads local files only. It never connects to or writes a device.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WTS names and reference slot sizes")
    parser.add_argument("bank", type=Path)
    parser.add_argument("layout", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    slots = {name: int(size) for name, size in layout["prompts"].items()}
    files = {path.stem: path for path in args.bank.glob("*.wts") if path.is_file()}
    missing = sorted(set(slots) - set(files))
    extra = sorted(set(files) - set(slots))
    if missing or extra:
        if missing:
            print("FAIL missing: " + ", ".join(missing))
        if extra:
            print("FAIL extra: " + ", ".join(extra))
        return 1

    manifest = {
        "schemaVersion": 1,
        "bank": str(args.bank),
        "layout": str(args.layout),
        "referenceFirmwareSha256": layout["source"]["sha256"],
        "deviceWritten": False,
        "files": {},
    }
    failed = False
    total = 0
    for name, slot_size in slots.items():
        path = files[name]
        size = path.stat().st_size
        total += size
        fits = 0 < size <= slot_size
        failed |= not fits
        manifest["files"][name] = {
            "path": str(path),
            "size": size,
            "referenceSlotSize": slot_size,
            "remainingBytes": slot_size - size,
            "fits": fits,
            "sha256": sha256(path),
        }
        print(f"{'PASS' if fits else 'FAIL'} {name:10} {size:5}/{slot_size:5} byte")

    manifest["totalPayloadSize"] = total
    manifest["referenceIndexedPayloadSize"] = int(layout["indexedPayloadSize"])
    manifest["totalFits"] = total <= int(layout["indexedPayloadSize"])
    failed |= not manifest["totalFits"]
    print(
        f"{'PASS' if manifest['totalFits'] else 'FAIL'} total      "
        f"{total:5}/{layout['indexedPayloadSize']:5} byte"
    )

    manifest_path = args.manifest or args.bank / "reference-fit.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Manifest: {manifest_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
