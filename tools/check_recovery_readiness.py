#!/usr/bin/env python3
"""Fail-closed recovery preflight for EutherBlue firmware experiments.

This tool only reads local files.  It has no Bluetooth transport and cannot
start, cancel, or otherwise influence an OTA operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_STOCK = {
    "filename": "HP206_UGREEN_Studio_Pro_V0.2.9.ufw",
    "size": 2_181_056,
    "sha256": "41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def newest_capture(capture_dir: Path) -> Path | None:
    captures = sorted(capture_dir.glob("target-info-*.json"))
    return captures[-1] if captures else None


def load_target_info(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        return None, "no target-info capture found"
    try:
        capture = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, f"could not read {path}: {error}"

    for frame in capture.get("frames", []):
        target = frame.get("targetInfo")
        if isinstance(target, dict):
            return target, None
    return None, f"no parsed targetInfo in {path}"


def inspect_file(path: Path, expected_size: int, expected_sha256: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "expectedSize": expected_size,
        "expectedSha256": expected_sha256,
        "size": None,
        "sha256": None,
        "verified": False,
    }
    if path.is_file():
        result["size"] = path.stat().st_size
        result["sha256"] = sha256(path)
        result["verified"] = (
            result["size"] == expected_size and result["sha256"] == expected_sha256
        )
    return result


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    stock = inspect_file(args.stock, EXPECTED_STOCK["size"], EXPECTED_STOCK["sha256"])
    capture_path = args.capture or newest_capture(args.capture_dir)
    target, capture_error = load_target_info(capture_path)

    double_backup = bool(target and target.get("supportsDoubleBackup") is True)
    no_bootloader_handoff = bool(target and target.get("needsBootLoader") is False)
    identity_matches = bool(
        target
        and target.get("projectCode") == "jl_sdk_ac697_publish"
        and target.get("protocolVersion") == "V_2.0"
    )

    gates = {
        "officialStockImageVerified": stock["verified"],
        "targetIdentityMatchesCapture": identity_matches,
        "targetReportsDoubleBackup": double_backup,
        "targetNeedsNoBootLoaderHandoff": no_bootloader_handoff,
        # These may only become true after documented physical tests.  They are
        # intentionally not inferred from a flag, SDK source, or successful build.
        "installedV025RecoveryImageSaved": False,
        "officialStockRestoreTestedOnThisHeadset": False,
        "automaticHardRollbackTestedOnThisHeadset": False,
    }

    return {
        "operation": "local read-only recovery preflight",
        "canWriteFirmware": False,
        "stock": stock,
        "capture": {
            "path": str(capture_path) if capture_path else None,
            "error": capture_error,
            "protocolVersion": target.get("protocolVersion") if target else None,
            "projectCode": target.get("projectCode") if target else None,
            "supportsDoubleBackup": target.get("supportsDoubleBackup") if target else None,
            "needsBootLoader": target.get("needsBootLoader") if target else None,
        },
        "gates": gates,
        "readyForModifiedFlash": all(gates.values()),
        "nextRequiredProof": [name for name, passed in gates.items() if not passed],
    }


def print_human(report: dict[str, Any]) -> None:
    print("EutherBlue recovery preflight (read-only)")
    for name, passed in report["gates"].items():
        print(f"  {'PASS' if passed else 'STOP'}  {name}")
    print()
    if report["readyForModifiedFlash"]:
        print("READY: all recovery gates are proven.")
    else:
        print("NOT READY: modified firmware must not be flashed.")
        print("Missing proof: " + ", ".join(report["nextRequiredProof"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stock",
        type=Path,
        default=Path("artifacts/original/firmware") / EXPECTED_STOCK["filename"],
    )
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--capture-dir", type=Path, default=Path("artifacts/captures"))
    parser.add_argument("--json", action="store_true", help="print the complete JSON report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human(report)
    return 0 if report["readyForModifiedFlash"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
