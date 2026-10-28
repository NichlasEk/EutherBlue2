#!/usr/bin/env python3
"""Delete only the exact captured previous upgrade context, then reboot."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket

from read_hd350_gaia_file import Gaia
from probe_hd350_hidden_usb_audio import check_stock


EXPECTED = bytes.fromhex(
    "00000001000000010000000000010001000100020000197326db0006000a0000000000000000"
)
EXPECTED_SHA = "52152aea9470b051dfdb30fd4266a6ac15e8d8312a4e5300efdf31daae58f703"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", type=int, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    check_stock()
    if hashlib.sha256(EXPECTED).hexdigest() != EXPECTED_SHA:
        raise ValueError("pinned previous-context hash mismatch")
    guard = {
        "expectedContextSha256": EXPECTED_SHA,
        "expectedSessionId": "26db1973",
        "expectedResumeWord13": 6,
        "expectedLastClosedPartitionWord14": 10,
        "operation": "delete ConfigStore key 4 and reset only after exact readback",
        "imageDataSent": False,
        "bankSwapRequested": False,
    }
    if not args.execute:
        print(json.dumps(guard, indent=2))
        return 0
    if args.output is None:
        parser.error("--output required with --execute")
    if args.output.exists():
        raise ValueError("capture already exists")
    result = dict(guard)
    result.update({"transactions": [], "replies": {}, "mutationAttempted": False})
    with args.output.open("x+") as capture:
        def save() -> None:
            capture.seek(0)
            json.dump(result, capture, indent=2)
            capture.write("\n")
            capture.truncate()
            capture.flush()
            os.fsync(capture.fileno())

        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(8)
        gaia = Gaia(sock, result["transactions"])

        def query(name, command, payload=b"", vendor=10):
            reply = gaia.query(vendor, command, payload)
            result["replies"][name] = reply.hex()
            save()
            return reply

        try:
            sock.connect(("00:00:00:00:00:00", args.channel))
            if query("version", 0x280, vendor=0x494) != bytes.fromhex("00000500050000"):
                raise ValueError("firmware 5.5.0 not confirmed")
            if query("bootMode", 0x282) != b"\0\0":
                raise ValueError("not in normal boot mode")
            before = query("contextBefore", 0x710, b"\0\4")
            if before != b"\0\0\4" + EXPECTED:
                raise ValueError("live context is not the exact captured previous context; no deletion")
            result["mutationAttempted"] = True
            save()
            if query("deletePreviousContext", 0x712, b"\0\4") != b"\0":
                raise ValueError("context deletion rejected")
            if query("contextAfter", 0x710, b"\0\4") != b"\5":
                raise ValueError("context deletion readback failed; no reset")
            result["deletionReadbackVerified"] = True
            save()
            if query("resetAfterDelete", 0x202, b"\0") != b"\0":
                raise ValueError("reset rejected")
            result["resetRequested"] = True
        except Exception as error:
            result["error"] = str(error)
        finally:
            sock.close()
            save()
    print(json.dumps({key: value for key, value in result.items() if key != "transactions"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
