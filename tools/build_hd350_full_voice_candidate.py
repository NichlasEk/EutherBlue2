#!/usr/bin/env python3
"""Build an offline HD 350BT candidate with all 13 exact-size prompts replaced."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verify_hd350_signature import load_key, parse, verify


STOCK_SHA256 = "25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resources",
        type=Path,
        default=Path("artifacts/build/hd350bt-christian-grosshandlare-resources"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/build/hd350bt-Christian-Grosshandlare-full-UNSIGNED"),
    )
    args = parser.parse_args()

    base = Path("artifacts/extracted/hd350bt")
    stock_path = base / "firmware-5.5.0/HD350_firmware_v5.5.0.bin"
    stock = stock_path.read_bytes()
    if digest(stock) != STOCK_SHA256:
        raise ValueError("unexpected original firmware")
    inventory = json.loads((base / "inspection-5.5.0/inventory.json").read_text())
    block = next(item for item in inventory["blocks"] if item.get("partition") == 7)
    entries = {
        int(item["path"].removeprefix("prompts/").removesuffix(".prm")): item
        for item in block["files"]
        if item["path"].startswith("prompts/")
    }
    if set(entries) != set(range(13)):
        raise ValueError(f"unexpected prompt inventory: {sorted(entries)}")

    parts, positions, _ = parse(stock)
    candidate = bytearray(stock)
    replacements: list[dict[str, object]] = []
    changed_offsets: set[int] = set()
    for prompt_id in range(13):
        entry = entries[prompt_id]
        start = positions[7] + int(entry["offset"])
        end = start + int(entry["size"])
        original = stock[start:end]
        if digest(original) != entry["sha256"]:
            raise ValueError(f"original prompt mismatch for {prompt_id}")
        replacement_path = args.resources / f"{prompt_id}.prm"
        replacement = replacement_path.read_bytes()
        if len(replacement) != len(original) or len(replacement) % 128:
            raise ValueError(f"prompt {prompt_id} does not preserve the exact SBC slot size")
        candidate[start:end] = replacement
        changed = sum(left != right for left, right in zip(original, replacement, strict=True))
        changed_offsets.update(
            start + index
            for index, (left, right) in enumerate(zip(original, replacement, strict=True))
            if left != right
        )
        replacements.append(
            {
                "id": prompt_id,
                "fileOffset": start,
                "bytes": len(replacement),
                "changedBytes": changed,
                "originalSha256": digest(original),
                "replacementSha256": digest(replacement),
                "replacement": str(replacement_path),
            }
        )

    candidate_bytes = bytes(candidate)
    new_parts, new_positions, _ = parse(candidate_bytes)
    if new_positions != positions:
        raise ValueError("firmware layout changed")
    if any(new_parts[number] != parts[number] for number in parts if number != 7):
        raise ValueError("a non-resource partition changed")
    allowed = {
        positions[7] + int(entry["offset"]) + offset
        for entry in entries.values()
        for offset in range(int(entry["size"]))
    }
    actual = {index for index, (left, right) in enumerate(zip(stock, candidate_bytes, strict=True)) if left != right}
    if actual != changed_offsets or not actual.issubset(allowed):
        raise ValueError("candidate changed bytes outside the 13 prompt payloads")

    trust = (base / "firmware-5.8.0/HD350BT_firmware_v580_DFU.bin").read_bytes()
    key = load_key(trust)
    if not verify(stock, key)["signatureValid"]:
        raise ValueError("stock signature did not verify")
    if verify(candidate_bytes, key)["signatureValid"]:
        raise ValueError("modified candidate unexpectedly retained the stock signature")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    image = args.output_dir / "HD350BT-5.5.0-Christian-Grosshandlare-full-UNSIGNED.bin"
    image.write_bytes(candidate_bytes)
    resource_manifest = json.loads((args.resources / "manifest.json").read_text())
    manifest = {
        "status": "UNSIGNED FULL VOICE CANDIDATE; exact-size prompt-only modification",
        "file": str(image),
        "size": len(candidate_bytes),
        "sha256": digest(candidate_bytes),
        "stock": str(stock_path),
        "stockSha256": digest(stock),
        "signatureValid": False,
        "newCandidatePhysicallyTested": False,
        "transferMechanismPreviouslyPhysicallyProven": True,
        "speechTempoChanged": False,
        "speechTruncated": False,
        "filesystemMetadataChanged": False,
        "onlyChangedFiles": [f"prompts/{prompt_id}.prm" for prompt_id in range(13)],
        "changedBytes": len(actual),
        "replacements": replacements,
        "voiceResourceManifest": str(args.resources / "manifest.json"),
        "texts": {
            prompt_id: item["text"]
            for prompt_id, item in resource_manifest["prompts"].items()
        },
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
