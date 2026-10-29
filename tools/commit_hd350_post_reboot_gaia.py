#!/usr/bin/env python3
"""Complete the exact HD 350BT d5f037da post-reboot session over GAIA."""
from local_device import bluetooth_address

import argparse
import json
import os
from pathlib import Path
import socket
import time

from probe_hd350_resume_state import ObserveGaia
from probe_hd350_hidden_usb_audio import check_stock


EXPECTED_CONTEXT = bytes.fromhex(
    "0000000100000001000000000001000100010002000037dad5f00003000a0000000000000000"
)


def next_vm_event(gaia: ObserveGaia, opcodes: set[int], timeout: float = 12) -> bytes:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for entry in gaia.log:
            for raw in entry.get("frames", []):
                frame = bytes.fromhex(raw)
                if frame[4:8] != bytes.fromhex("000a4003"):
                    continue
                payload = frame[8:8 + frame[3]]
                if len(payload) < 4 or payload[0] != 0x12:
                    continue
                if raw not in gaia.seen:
                    gaia.sock.sendall(bytes.fromhex("ff010002000ac0030012"))
                    gaia.seen.add(raw)
                    vm = payload[1:]
                    if len(vm) != 3 + int.from_bytes(vm[1:3], "big"):
                        raise ValueError("malformed VM notification")
                    if vm[0] in opcodes:
                        return vm
        if len(gaia.buffer) >= 8:
            if gaia.buffer[:2] != b"\xff\x01" or gaia.buffer[2] & ~1:
                raise ValueError("unexpected GAIA frame")
            size = 8 + gaia.buffer[3] + (gaia.buffer[2] & 1)
            if len(gaia.buffer) >= size:
                frame = bytes(gaia.buffer[:size])
                del gaia.buffer[:size]
                if frame[2] & 1:
                    checksum = 0
                    for byte in frame:
                        checksum ^= byte
                    if checksum:
                        raise ValueError("bad GAIA checksum")
                gaia.log.append({"frames": [frame.hex()]})
                continue
        gaia.sock.settimeout(max(0.01, deadline - time.monotonic()))
        data = gaia.sock.recv(1024)
        if not data:
            raise EOFError("GAIA connection closed")
        gaia.buffer.extend(data)
        if len(gaia.buffer) > 8192:
            raise ValueError("GAIA buffer limit")
    raise TimeoutError("expected post-reboot VM event missing")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", type=int, default=1)
    parser.add_argument("--wait-seconds", type=int, default=75)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    check_stock()
    guard = {
        "sessionId": "d5f037da",
        "expectedContextHex": EXPECTED_CONTEXT.hex(),
        "expectedResumeWord13": 3,
        "expectedLastClosedPartitionWord14": 10,
        "imageDataSent": False,
        "abortSent": False,
        "commitCfmOnlyIfRequested": True,
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

        sock = None
        gaia = None

        def query(name, command, payload=b"", vendor=10):
            reply = gaia.query(vendor, command, payload)
            result["replies"][name] = reply.hex()
            save()
            return reply

        def success(name, command, payload=b""):
            reply = query(name, command, payload)
            if reply != b"\0":
                raise ValueError(name + " rejected: " + reply.hex())

        connected = False
        try:
            deadline = time.monotonic() + args.wait_seconds
            result["connectionAttempts"] = 0
            while time.monotonic() < deadline:
                candidate = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                candidate.settimeout(2)
                result["connectionAttempts"] += 1
                try:
                    candidate.connect((bluetooth_address(), args.channel))
                    sock = candidate
                    gaia = ObserveGaia(sock, result["transactions"])
                    result["connectedAtMonotonic"] = time.monotonic()
                    save()
                    break
                except OSError as error:
                    result["lastConnectError"] = str(error)
                    candidate.close()
                    time.sleep(0.2)
            if sock is None or gaia is None:
                raise TimeoutError("GAIA did not become reachable within post-reboot window")
            sock.settimeout(8)
            if query("version", 0x280, vendor=0x494) != bytes.fromhex("00000500050000"):
                raise ValueError("firmware 5.5.0 not confirmed")
            if query("bootMode", 0x282) != b"\0\0":
                raise ValueError("not normal boot mode")
            if query("contextBefore", 0x710, b"\0\4") != b"\0\0\4" + EXPECTED_CONTEXT:
                raise ValueError("live context is not exact d5f037da POST_REBOOT; no handshake")
            registration = query("registerVMNotifications", 0x4001, b"\x12")
            if registration not in (b"\0", b"\0\x12"):
                raise ValueError("VM notification registration rejected")
            success("upgradeConnect", 0x640)
            connected = True
            result["mutationAttempted"] = True
            save()
            success("syncAfterReboot", 0x642, bytes.fromhex("180000"))
            event = next_vm_event(gaia, {0x0D, 0x11})
            result["inProgressInd"] = event.hex()
            if event[0] == 0x11:
                raise RuntimeError("error before in-progress response: " + event.hex())
            success("inProgressResponse", 0x642, bytes.fromhex("0e000100"))
            result["inProgressResponseSent"] = True
            save()
            event = next_vm_event(gaia, {0x0F, 0x11, 0x12}, timeout=20)
            if event[0] == 0x11:
                raise RuntimeError("commit validation error: " + event.hex())
            if event[0] == 0x0F:
                result["commitReq"] = event.hex()
                success("commitConfirm", 0x642, bytes.fromhex("10000100"))
                result["commitCfmSent"] = True
                save()
                event = next_vm_event(gaia, {0x11, 0x12}, timeout=20)
            if event[0] == 0x11:
                raise RuntimeError("commit error: " + event.hex())
            result["completeInd"] = event.hex()
            result["completed"] = True
            save()
            success("upgradeDisconnect", 0x641)
            connected = False
        except Exception as error:
            result["error"] = str(error)
            if connected:
                try:
                    success("safeDisconnect", 0x641)
                    result["safeDisconnectSent"] = True
                except Exception as disconnect_error:
                    result["disconnectError"] = str(disconnect_error)
        finally:
            if sock is not None:
                sock.close()
            save()
    print(json.dumps({key: value for key, value in result.items() if key != "transactions"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
