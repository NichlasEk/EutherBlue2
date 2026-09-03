#!/usr/bin/env python3
"""Rebuild a fixed-size JieLi JLFS tone library with optional replacements."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path


HEADER_SIZE = 32
ALIGNMENT = 16


def jl_crc16(data: bytes, initial: int = 0) -> int:
    crc = initial
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def align(value: int, alignment: int = ALIGNMENT) -> int:
    return (value + alignment - 1) // alignment * alignment


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Entry:
    name: str
    raw_name: bytes
    data_crc: int
    offset: int
    size: int
    flags: int
    reserved: int
    index: int
    data: bytes


def parse_header(buffer: bytes, offset: int) -> tuple[int, int, int, int, int, int, bytes]:
    stored_header_crc, header = struct.unpack_from("<H30s", buffer, offset)
    calculated = jl_crc16(header)
    if stored_header_crc != calculated:
        raise ValueError(
            f"fel header-CRC vid 0x{offset:x}: 0x{stored_header_crc:04x} != 0x{calculated:04x}"
        )
    return struct.unpack("<HIIBBH16s", header)


def parse_library(buffer: bytes) -> tuple[tuple[int, int, int, int, int, int, bytes], list[Entry]]:
    outer = parse_header(buffer, 0)
    outer_data_crc, outer_offset, outer_size, outer_flags, _, _, raw_outer_name = outer
    if outer_offset != HEADER_SIZE or outer_size != len(buffer) or outer_flags != 0x83:
        raise ValueError("oväntad yttre JLFS-header")
    if jl_crc16(buffer[HEADER_SIZE:]) != outer_data_crc:
        raise ValueError("fel data-CRC för ursprungligt röstbibliotek")
    if raw_outer_name.split(b"\0", 1)[0] not in {b"tone_en", b"tone_zh"}:
        raise ValueError("filen är inte ett känt röstbibliotek")

    entries: list[Entry] = []
    header_offset = HEADER_SIZE
    while True:
        data_crc, data_offset, size, flags, reserved, index, raw_name = parse_header(
            buffer, header_offset
        )
        end = data_offset + size
        if data_offset < HEADER_SIZE or end > len(buffer):
            raise ValueError(f"ogiltigt dataområde vid 0x{header_offset:x}")
        data = buffer[data_offset:end]
        if jl_crc16(data) != data_crc:
            raise ValueError(f"fel data-CRC för {raw_name!r}")
        name = raw_name.split(b"\0", 1)[0].decode("ascii")
        entries.append(
            Entry(name, raw_name, data_crc, data_offset, size, flags, reserved, index, data)
        )
        header_offset += HEADER_SIZE
        if index:
            break
    if header_offset > min(entry.offset for entry in entries):
        raise ValueError("JLFS-headerområdet överlappar data")
    return outer, entries


def make_header(
    data_crc: int,
    offset: int,
    size: int,
    flags: int,
    reserved: int,
    index: int,
    raw_name: bytes,
) -> bytes:
    fields = struct.pack(
        "<HIIBBH16s", data_crc, offset, size, flags, reserved, index, raw_name
    )
    return struct.pack("<H30s", jl_crc16(fields), fields)


def rebuild(
    original: bytes,
    replacement_dir: Path | None,
    preserve_layout: bool = False,
) -> tuple[bytes, dict]:
    outer, entries = parse_library(original)
    replacements: dict[str, bytes] = {}
    if replacement_dir is not None:
        for path in replacement_dir.glob("*.wts"):
            replacements[path.name] = path.read_bytes()
        unknown = replacements.keys() - {entry.name for entry in entries}
        if unknown:
            raise ValueError("okända ersättningsfiler: " + ", ".join(sorted(unknown)))

    if preserve_layout:
        result = bytearray(original)
        manifest_entries = []
        for position, entry in enumerate(entries):
            data = replacements.get(entry.name, entry.data)
            next_offset = (
                entries[position + 1].offset
                if position + 1 < len(entries)
                else len(original)
            )
            capacity = next_offset - entry.offset
            if len(data) > capacity:
                raise ValueError(
                    f"{entry.name} är {len(data)} byte men det fasta utrymmet är "
                    f"bara {capacity} byte"
                )
            header_offset = HEADER_SIZE + position * HEADER_SIZE
            result[header_offset : header_offset + HEADER_SIZE] = make_header(
                jl_crc16(data),
                entry.offset,
                len(data),
                entry.flags,
                entry.reserved,
                entry.index,
                entry.raw_name,
            )
            result[entry.offset : next_offset] = b"\xFF" * capacity
            result[entry.offset : entry.offset + len(data)] = data
            manifest_entries.append(
                {
                    "name": entry.name,
                    "offset": entry.offset,
                    "originalOffset": entry.offset,
                    "size": len(data),
                    "originalSize": entry.size,
                    "capacity": capacity,
                    "sha256": sha256(data),
                    "replaced": entry.name in replacements,
                }
            )

        (
            _,
            outer_offset,
            outer_size,
            outer_flags,
            outer_reserved,
            outer_index,
            outer_name,
        ) = outer
        body = bytes(result[HEADER_SIZE:])
        result[:HEADER_SIZE] = make_header(
            jl_crc16(body),
            outer_offset,
            outer_size,
            outer_flags,
            outer_reserved,
            outer_index,
            outer_name,
        )
        rebuilt = bytes(result)
        _, rebuilt_entries = parse_library(rebuilt)
        if [entry.offset for entry in rebuilt_entries] != [entry.offset for entry in entries]:
            raise ValueError("en intern offset ändrades trots --preserve-layout")
        return rebuilt, {
            "originalSize": len(original),
            "rebuiltSize": len(rebuilt),
            "usedBytes": max(entry.offset + entry.size for entry in rebuilt_entries),
            "freeBytes": sum(
                item["capacity"] - item["size"] for item in manifest_entries
            ),
            "originalSha256": sha256(original),
            "rebuiltSha256": sha256(rebuilt),
            "byteIdentical": rebuilt == original,
            "layoutPreserved": True,
            "entries": manifest_entries,
        }

    data_offset = align(HEADER_SIZE + len(entries) * HEADER_SIZE)
    headers = bytearray()
    data_area = bytearray(b"\xFF" * (data_offset - HEADER_SIZE - len(entries) * HEADER_SIZE))
    manifest_entries = []
    for entry in entries:
        data = replacements.get(entry.name, entry.data)
        headers.extend(
            make_header(
                jl_crc16(data),
                data_offset,
                len(data),
                entry.flags,
                entry.reserved,
                entry.index,
                entry.raw_name,
            )
        )
        data_area.extend(data)
        padding = align(len(data)) - len(data)
        data_area.extend(b"\xFF" * padding)
        manifest_entries.append(
            {
                "name": entry.name,
                "offset": data_offset,
                "size": len(data),
                "sha256": sha256(data),
                "replaced": entry.name in replacements,
            }
        )
        data_offset += len(data) + padding

    outer_data_size = len(original) - HEADER_SIZE
    body = bytes(headers + data_area)
    if len(body) > outer_data_size:
        raise ValueError(
            f"röstbiblioteket är {len(body) + HEADER_SIZE} byte men får högst vara {len(original)}"
        )
    body += b"\xFF" * (outer_data_size - len(body))
    _, outer_offset, outer_size, outer_flags, outer_reserved, outer_index, outer_name = outer
    outer_header = make_header(
        jl_crc16(body),
        outer_offset,
        outer_size,
        outer_flags,
        outer_reserved,
        outer_index,
        outer_name,
    )
    result = outer_header + body
    parse_library(result)
    return result, {
        "originalSize": len(original),
        "rebuiltSize": len(result),
        "usedBytes": data_offset,
        "freeBytes": len(result) - data_offset,
        "originalSha256": sha256(original),
        "rebuiltSha256": sha256(result),
        "byteIdentical": result == original,
        "layoutPreserved": False,
        "entries": manifest_entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild a fixed-size JieLi tone library")
    parser.add_argument("original", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--replacements", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--preserve-layout",
        action="store_true",
        help="keep every original entry offset and reject replacements that do not fit",
    )
    parser.add_argument(
        "--require-identical",
        action="store_true",
        help="fail unless the rebuilt file is byte-identical to the original",
    )
    args = parser.parse_args()
    original = args.original.read_bytes()
    rebuilt, manifest = rebuild(original, args.replacements, args.preserve_layout)
    if args.require_identical and not manifest["byteIdentical"]:
        raise SystemExit("Roundtrippen blev inte byte-identisk")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rebuilt)
    manifest_path = args.manifest or args.output.with_suffix(args.output.suffix + ".json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
