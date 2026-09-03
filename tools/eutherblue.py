#!/usr/bin/env python3
"""Inspect and validate EutherBlue model profiles without touching hardware."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILE_ROOT = REPO_ROOT / "profiles"
PROFILE_ID = re.compile(r"^[a-z0-9][a-z0-9-]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
KNOWN_DRIVERS = {"jieli-ufw-boot-crc-v1"}


def profile_path(profile_id: str) -> Path:
    if not PROFILE_ID.fullmatch(profile_id):
        raise ValueError(f"ogiltigt profil-id: {profile_id!r}")
    return PROFILE_ROOT / profile_id / "profile.json"


def load_profile(profile_id: str) -> dict[str, Any]:
    path = profile_path(profile_id)
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"profilen finns inte: {profile_id}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"ogiltig JSON i {path}: {error}") from error
    if not isinstance(profile, dict):
        raise ValueError(f"profilen måste vara ett JSON-objekt: {path}")
    return profile


def nested(profile: dict[str, Any], dotted_key: str) -> Any:
    value: Any = profile
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"profilfältet saknas: {dotted_key}")
        value = value[part]
    return value


def safe_repo_path(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} måste vara en relativ sökväg")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} får inte lämna repot: {value}")
    return REPO_ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(
    profile: dict[str, Any], check_artifacts: bool, expected_id: str | None = None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    notes: list[str] = []
    required = {
        "schemaVersion",
        "id",
        "manufacturer",
        "model",
        "status",
        "hardware",
        "transport",
        "firmware",
        "voice",
        "build",
        "recovery",
    }
    missing = sorted(required - profile.keys())
    if missing:
        errors.append("saknade toppfält: " + ", ".join(missing))
        return errors, notes
    if profile["schemaVersion"] != 1:
        errors.append("schemaVersion måste vara 1")
    if not isinstance(profile["id"], str) or not PROFILE_ID.fullmatch(profile["id"]):
        errors.append("id måste vara ett säkert kebab-case-id")
    elif expected_id is not None and profile["id"] != expected_id:
        errors.append(f"profilens id måste matcha katalogen: {expected_id}")
    if profile["status"] not in {"research", "buildable", "working"}:
        errors.append("status måste vara research, buildable eller working")
    try:
        driver = nested(profile, "build.driver")
        if driver not in KNOWN_DRIVERS:
            errors.append(f"okänd byggdrivrutin: {driver}")
        stock_sha = nested(profile, "firmware.stock.sha256")
        if not isinstance(stock_sha, str) or not SHA256.fullmatch(stock_sha):
            errors.append("firmware.stock.sha256 är inte en SHA-256")
        verified_sha = nested(profile, "build.verifiedSha256")
        if not isinstance(verified_sha, str) or not SHA256.fullmatch(verified_sha):
            errors.append("build.verifiedSha256 är inte en SHA-256")
        bank_entries = nested(profile, "firmware.banks.entries")
        if bank_entries != ["flash.bin", "flash2.bin"]:
            errors.append("JieLi-drivrutinen kräver flash.bin och flash2.bin")
        for key in (
            "firmware.stock.path",
            "firmware.extractedPath",
            "firmware.decryptedFlashPath",
            "voice.originalPath",
            "voice.tempoMap",
            "voice.previewPath",
            "build.outputDirectory",
            "recovery.report",
        ):
            safe_repo_path(nested(profile, key), key)
    except ValueError as error:
        errors.append(str(error))

    forbidden = {"authkey", "password", "token", "privatekey", "secret"}

    def inspect_keys(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower().replace("_", "") in forbidden:
                    errors.append(f"hemligt fält är förbjudet i profiler: {key}")
                inspect_keys(child)
        elif isinstance(value, list):
            for child in value:
                inspect_keys(child)

    inspect_keys(profile)
    if check_artifacts and not errors:
        stock_path = safe_repo_path(nested(profile, "firmware.stock.path"), "stock.path")
        if not stock_path.is_file():
            errors.append(f"stockfilen saknas: {stock_path.relative_to(REPO_ROOT)}")
        else:
            actual_size = stock_path.stat().st_size
            expected_size = nested(profile, "firmware.stock.size")
            actual_sha = sha256(stock_path)
            if actual_size != expected_size:
                errors.append(f"stockfilens storlek är {actual_size}, väntade {expected_size}")
            if actual_sha != nested(profile, "firmware.stock.sha256"):
                errors.append("stockfilens SHA-256 stämmer inte")
            notes.append(f"stock SHA-256: {actual_sha}")
        output = safe_repo_path(nested(profile, "build.outputDirectory"), "build.outputDirectory")
        output /= nested(profile, "build.outputFilename")
        if not output.is_file():
            errors.append(f"det verifierade bygget saknas: {output.relative_to(REPO_ROOT)}")
        else:
            actual_sha = sha256(output)
            if actual_sha != nested(profile, "build.verifiedSha256"):
                errors.append("det verifierade byggets SHA-256 stämmer inte")
            notes.append(f"working SHA-256: {actual_sha}")
    return errors, notes


def list_profiles() -> list[dict[str, Any]]:
    profiles = []
    for path in sorted(PROFILE_ROOT.glob("*/profile.json")):
        profile = load_profile(path.parent.name)
        profiles.append(profile)
    return profiles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list model profiles")
    show = commands.add_parser("show", help="show one profile")
    show.add_argument("profile")
    show.add_argument("--json", action="store_true")
    check = commands.add_parser("check", help="validate one profile")
    check.add_argument("profile")
    check.add_argument("--artifacts", action="store_true")
    get = commands.add_parser("get", help="print one profile value")
    get.add_argument("profile")
    get.add_argument("key")
    args = parser.parse_args()

    try:
        if args.command == "list":
            for profile in list_profiles():
                print(f"{profile['id']:<20} {profile['status']:<9} {profile['manufacturer']} {profile['model']}")
            return 0
        profile = load_profile(args.profile)
        if args.command == "show":
            if args.json:
                print(json.dumps(profile, indent=2, ensure_ascii=False))
            else:
                print(f"{profile['manufacturer']} {profile['model']} ({profile['id']})")
                print(f"Status: {profile['status']}")
                print(f"Chip:   {nested(profile, 'hardware.chipFamily')}")
                print(f"Driver: {nested(profile, 'build.driver')}")
                print(f"Stock:  {nested(profile, 'firmware.stock.version')}")
                print(f"Voice:  {nested(profile, 'voice.format')}")
            return 0
        if args.command == "get":
            value = nested(profile, args.key)
            if isinstance(value, (dict, list)):
                print(json.dumps(value, separators=(",", ":"), ensure_ascii=False))
            elif isinstance(value, bool):
                print("true" if value else "false")
            else:
                print(value)
            return 0
        errors, notes = validate(profile, args.artifacts, args.profile)
        for note in notes:
            print(f"PASS  {note}")
        if errors:
            for error in errors:
                print(f"FAIL  {error}", file=sys.stderr)
            return 1
        print(f"PASS  profile {profile['id']} ({profile['status']})")
        return 0
    except ValueError as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
