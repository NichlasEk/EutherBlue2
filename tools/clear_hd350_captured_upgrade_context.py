#!/usr/bin/env python3
"""Delete only an exactly captured partial HD 350BT staging context."""

from __future__ import annotations
from local_device import bluetooth_address

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket

from probe_hd350_hidden_usb_audio import check_stock
from read_hd350_gaia_file import Gaia


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", type=int, required=True)
    parser.add_argument("--context-capture", type=Path, required=True)
    parser.add_argument("--stage-capture", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    check_stock()

    observed = json.loads(args.context_capture.read_text())
    staged = json.loads(args.stage_capture.read_text())
    context = bytes.fromhex(observed["contextHex"])
    words = [int.from_bytes(context[index : index + 2], "big") for index in range(0, len(context), 2)]
    session_id = bytes.fromhex(staged["sessionId"])
    expected_session_words = [
        int.from_bytes(session_id[2:4], "big"),
        int.from_bytes(session_id[0:2], "big"),
    ]
    if not (
        observed.get("contextPresent") is True
        and observed.get("replies", {}).get("version") == "00000500050000"
        and observed.get("replies", {}).get("bootMode") == "0000"
        and "error" not in observed
        and len(words) == 19
        and words[11:13] == expected_session_words
        and words[13] == 0
        and 0 <= words[14] <= 10
        and staged.get("candidateSha256")
        and staged.get("bytesSent", 0) > 0
        and staged.get("fileCursor") == staged.get("bytesSent")
        and staged.get("footerSent") is False
        and staged.get("bankSwapRequested") is False
        and staged.get("error")
    ):
        raise ValueError("captured partial-staging context/evidence guard failed")

    guard = {
        "candidateSha256": staged["candidateSha256"],
        "sessionId": staged["sessionId"],
        "expectedContextSha256": hashlib.sha256(context).hexdigest(),
        "expectedResumeWord13": words[13],
        "expectedLastClosedPartitionWord14": words[14],
        "partialBytesSent": staged["bytesSent"],
        "operation": "delete ConfigStore key 4 and reset only after exact live readback",
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
            sock.connect((bluetooth_address(), args.channel))
            if query("version", 0x280, vendor=0x494) != bytes.fromhex("00000500050000"):
                raise ValueError("firmware 5.5.0 not confirmed")
            if query("bootMode", 0x282) != b"\0\0":
                raise ValueError("not in normal boot mode")
            if query("contextBefore", 0x710, b"\0\4") != b"\0\0\4" + context:
                raise ValueError("live context differs from the exact capture; no deletion")
            result["mutationAttempted"] = True
            save()
            if query("deletePartialContext", 0x712, b"\0\4") != b"\0":
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
