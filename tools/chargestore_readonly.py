#!/usr/bin/env python3
"""Encode and decode a tiny read-only subset of JieLi chargestore frames.

The program has deliberately no serial-port or device I/O. It cannot emit the
factory-reset, DUT, storage, pairing-write, or update commands.
"""

from __future__ import annotations

import argparse
import json


SAFE_QUERIES = {
    "bluetooth-name": bytes((0x21, 0x01)),
    "sdk-version": bytes((0x21, 0x02)),
    "battery": bytes((0x21, 0x03)),
}


def crc8(data: bytes) -> int:
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8C if crc & 1 else crc >> 1
    return crc


def encode(payload: bytes) -> bytes:
    if not 0 < len(payload) <= 36:
        raise ValueError("payload must contain 1 to 36 bytes")
    frame = bytes((0x55, 0xAA, len(payload))) + payload
    return frame + bytes((crc8(frame),))


def decode(frame: bytes) -> bytes:
    if len(frame) < 4:
        raise ValueError("frame is shorter than the four-byte minimum")
    if frame[:2] not in {b"\x55\xaa", b"\x5a\xa5"}:
        raise ValueError("unknown sync word")
    expected_size = frame[2] + 4
    if len(frame) != expected_size:
        raise ValueError(f"frame has {len(frame)} bytes; expected {expected_size}")
    expected_crc = crc8(frame[:-1])
    if frame[-1] != expected_crc:
        raise ValueError(f"CRC mismatch: 0x{frame[-1]:02x} != 0x{expected_crc:02x}")
    return frame[3:-1]


def parse_hex(value: str) -> bytes:
    compact = value.replace(" ", "").replace(":", "")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline JieLi chargestore frame helper")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    encode_parser = subparsers.add_parser("encode", help="encode an allowlisted read query")
    encode_parser.add_argument("query", choices=sorted(SAFE_QUERIES))
    decode_parser = subparsers.add_parser("decode", help="validate and decode a captured frame")
    decode_parser.add_argument("frame", type=parse_hex)
    args = parser.parse_args()

    if args.operation == "encode":
        payload = SAFE_QUERIES[args.query]
        frame = encode(payload)
        print(json.dumps({"query": args.query, "payload": payload.hex(), "frame": frame.hex()}))
        return 0

    payload = decode(args.frame)
    result: dict[str, object] = {"payload": payload.hex(), "length": len(payload)}
    if len(payload) >= 2 and payload[:2] in SAFE_QUERIES.values():
        result["query"] = next(name for name, value in SAFE_QUERIES.items() if value == payload[:2])
        if payload[:2] in {SAFE_QUERIES["bluetooth-name"], SAFE_QUERIES["sdk-version"]}:
            result["text"] = payload[2:].decode("ascii", errors="replace")
        elif payload[:2] == SAFE_QUERIES["battery"] and len(payload) >= 5:
            result["millivoltsRaw"] = int.from_bytes(payload[2:4], "little")
            result["percent"] = payload[4]
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        raise SystemExit(f"FAIL: {exc}") from exc
