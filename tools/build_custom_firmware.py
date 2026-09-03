#!/usr/bin/env python3
"""Patch one fixed-size tone library into an existing JieLi UFW image.

The tool only writes a local file. It contains no Bluetooth or OTA transport.
It requires the original UFW plus the matching selectively decrypted flash image
created by the pinned read-only unpacker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path


UFW_HEADER_SIZE = 0x40
UFW_ENTRY_SIZE = 0x50
UFW_KEY = 0xFFFF


def jl_crc16(data: bytes, initial: int = 0) -> int:
    crc = initial
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def jl_enc_cipher(buffer: bytearray, offset: int, size: int, key: int = UFW_KEY) -> None:
    for index in range(size):
        buffer[offset + index] ^= key & 0xFF
        key = ((key << 1) ^ (0x1021 if key & 0x8000 else 0)) & 0xFFFF


def crypt_copy(data: bytes, key: int = UFW_KEY) -> bytes:
    result = bytearray(data)
    jl_enc_cipher(result, 0, len(result), key)
    return bytes(result)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class UfwEntry:
    header_offset: int
    entry_type: int
    index: int
    data_crc: int
    unknown1: int
    offset: int
    size: int
    padded_size: int
    unknown2: bytes
    name: str
    plain_header: bytes


def parse_ufw(image: bytes) -> tuple[bytearray, int, list[UfwEntry]]:
    if len(image) < UFW_HEADER_SIZE:
        raise ValueError("UFW-filen är för kort")
    header = bytearray(crypt_copy(image[:UFW_HEADER_SIZE]))
    stored_header_crc, list_crc, image_size, entry_count, _, _, _ = struct.unpack(
        "<HHIHHI48s", header
    )
    if image_size != len(image):
        raise ValueError(f"UFW-storleken i headern är {image_size}, faktisk {len(image)}")
    if jl_crc16(header[2:]) != stored_header_crc:
        raise ValueError("fel CRC i UFW-huvudheadern")
    list_end = UFW_HEADER_SIZE + entry_count * UFW_ENTRY_SIZE
    if list_end > len(image):
        raise ValueError("UFW-postlistan går utanför filen")
    if jl_crc16(image[UFW_HEADER_SIZE:list_end]) != list_crc:
        raise ValueError("fel CRC i UFW-postlistan")

    entries = []
    for offset in range(UFW_HEADER_SIZE, list_end, UFW_ENTRY_SIZE):
        plain = crypt_copy(image[offset : offset + UFW_ENTRY_SIZE])
        values = struct.unpack("<HHHHIII44s16s", plain)
        name = values[8].split(b"\0", 1)[0].decode("ascii")
        entry = UfwEntry(offset, *values[:7], values[7], name, plain)
        if entry.offset + entry.size > len(image):
            raise ValueError(f"UFW-posten {name} går utanför filen")
        actual_crc = jl_crc16(image[entry.offset : entry.offset + entry.size])
        # JieLi's own UFW loader requires this check for both double-bank flash
        # images. Other vendor-specific entry types reuse the 16-bit field with
        # differing semantics, so preserve those entries byte-for-byte without
        # guessing.
        if entry.name in {"flash.bin", "flash2.bin"} and actual_crc != entry.data_crc:
            raise ValueError(
                f"fel data-CRC för {name}: 0x{entry.data_crc:04x} != 0x{actual_crc:04x}"
            )
        entries.append(entry)
    return header, list_end, entries


def replace_flash_entry_crcs(
    image: bytearray,
    header: bytearray,
    list_end: int,
    updates: list[tuple[UfwEntry, int]],
) -> None:
    for entry, crc in updates:
        plain_entry = bytearray(entry.plain_header)
        struct.pack_into("<H", plain_entry, 4, crc)
        image[entry.header_offset : entry.header_offset + UFW_ENTRY_SIZE] = crypt_copy(
            plain_entry
        )
    struct.pack_into("<H", header, 2, jl_crc16(image[UFW_HEADER_SIZE:list_end]))
    struct.pack_into("<H", header, 0, jl_crc16(header[2:]))
    image[:UFW_HEADER_SIZE] = crypt_copy(header)


def patch_firmware(
    original_ufw: bytes,
    decrypted_flash: bytes,
    original_tone: bytes,
    replacement_tone: bytes,
) -> tuple[bytes, dict]:
    if len(replacement_tone) != len(original_tone):
        raise ValueError("ersättningscontainern måste ha exakt samma storlek som originalet")
    header, list_end, entries = parse_ufw(original_ufw)
    flash_entries = [entry for entry in entries if entry.name == "flash.bin"]
    if len(flash_entries) != 1:
        raise ValueError("förväntade exakt en flash.bin-post")
    flash_entry = flash_entries[0]
    mirror_entries = [entry for entry in entries if entry.name == "flash2.bin"]
    if len(mirror_entries) != 1:
        raise ValueError("förväntade exakt en flash2.bin-post för dubbelbanksbilden")
    mirror_entry = mirror_entries[0]
    if len(decrypted_flash) != flash_entry.size:
        raise ValueError("decrypted.bin matchar inte flash.bin-storleken")

    tone_offset = decrypted_flash.find(original_tone)
    if tone_offset < 0 or decrypted_flash.find(original_tone, tone_offset + 1) >= 0:
        raise ValueError("ursprunglig röstcontainer hittades inte exakt en gång")
    absolute_offset = flash_entry.offset + tone_offset
    original_ciphertext = original_ufw[absolute_offset : absolute_offset + len(original_tone)]
    if len(original_ciphertext) != len(original_tone):
        raise ValueError("röstregionen går utanför flash.bin")
    mirror_absolute_offset = mirror_entry.offset + tone_offset
    mirror_ciphertext = original_ufw[
        mirror_absolute_offset : mirror_absolute_offset + len(original_tone)
    ]
    if mirror_ciphertext != original_ciphertext:
        raise ValueError(
            "röstregionen är inte identisk i flash.bin och flash2.bin; vägrar gissa"
        )

    # JieLi SFC encryption is XOR based. Derive the exact keystream from the
    # matching original ciphertext/plaintext pair instead of approximating the
    # firmware packer's internal chunk boundaries.
    replacement_ciphertext = bytes(
        new ^ old_plain ^ old_cipher
        for new, old_plain, old_cipher in zip(
            replacement_tone, original_tone, original_ciphertext, strict=True
        )
    )
    result = bytearray(original_ufw)
    result[absolute_offset : absolute_offset + len(replacement_tone)] = replacement_ciphertext
    result[
        mirror_absolute_offset : mirror_absolute_offset + len(replacement_tone)
    ] = replacement_ciphertext
    new_flash_crc = jl_crc16(
        result[flash_entry.offset : flash_entry.offset + flash_entry.size]
    )
    new_mirror_crc = jl_crc16(
        result[mirror_entry.offset : mirror_entry.offset + mirror_entry.size]
    )
    replace_flash_entry_crcs(
        result,
        header,
        list_end,
        [(flash_entry, new_flash_crc), (mirror_entry, new_mirror_crc)],
    )
    rebuilt = bytes(result)

    # Reparse every UFW entry and independently recover the patched plaintext.
    parse_ufw(rebuilt)
    recovered = bytes(
        new_cipher ^ old_plain ^ old_cipher
        for new_cipher, old_plain, old_cipher in zip(
            rebuilt[absolute_offset : absolute_offset + len(original_tone)],
            original_tone,
            original_ciphertext,
            strict=True,
        )
    )
    if recovered != replacement_tone:
        raise ValueError("den inbyggda röstcontainern kunde inte verifieras efter kryptering")
    recovered_mirror = bytes(
        new_cipher ^ old_plain ^ old_cipher
        for new_cipher, old_plain, old_cipher in zip(
            rebuilt[
                mirror_absolute_offset : mirror_absolute_offset + len(original_tone)
            ],
            original_tone,
            mirror_ciphertext,
            strict=True,
        )
    )
    if recovered_mirror != replacement_tone:
        raise ValueError("röstcontainern kunde inte verifieras i flash2.bin")

    return rebuilt, {
        "originalUfwSha256": sha256(original_ufw),
        "rebuiltUfwSha256": sha256(rebuilt),
        "byteIdentical": rebuilt == original_ufw,
        "imageSize": len(rebuilt),
        "flashOffset": flash_entry.offset,
        "flashSize": flash_entry.size,
        "originalFlashCrc": f"0x{flash_entry.data_crc:04x}",
        "rebuiltFlashCrc": f"0x{new_flash_crc:04x}",
        "mirrorFlashOffset": mirror_entry.offset,
        "mirrorFlashSize": mirror_entry.size,
        "originalMirrorFlashCrc": f"0x{mirror_entry.data_crc:04x}",
        "rebuiltMirrorFlashCrc": f"0x{new_mirror_crc:04x}",
        "toneOffsetInFlash": tone_offset,
        "toneAbsoluteOffset": absolute_offset,
        "mirrorToneAbsoluteOffset": mirror_absolute_offset,
        "toneRegionMirrored": True,
        "toneSize": len(replacement_tone),
        "originalToneSha256": sha256(original_tone),
        "replacementToneSha256": sha256(replacement_tone),
        "ufwCrcsValid": True,
        "firmwareFlashed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local UFW with a fixed-size tone replacement")
    parser.add_argument("--original-ufw", type=Path, required=True)
    parser.add_argument("--decrypted-flash", type=Path, required=True)
    parser.add_argument("--original-tone", type=Path, required=True)
    parser.add_argument("--replacement-tone", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--require-identical", action="store_true")
    args = parser.parse_args()

    rebuilt, manifest = patch_firmware(
        args.original_ufw.read_bytes(),
        args.decrypted_flash.read_bytes(),
        args.original_tone.read_bytes(),
        args.replacement_tone.read_bytes(),
    )
    if args.require_identical and not manifest["byteIdentical"]:
        raise SystemExit("UFW-roundtrippen blev inte byte-identisk")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rebuilt)
    manifest_path = args.manifest or args.output.with_suffix(args.output.suffix + ".json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
