#!/usr/bin/env python3
"""Complete the guarded HD 350BT post-reboot handshake within its 60s window."""

import argparse
import errno
import fcntl
import json
import os
from pathlib import Path
import select
import time

from read_hd350_usb_features import EXPECTED
from stage_hd350_unsigned_candidate_usb import packet, receive, send_vm, transport_command


POST_SWAP_HID_IDS = {
    "0003:00000A12:00004007",
    "0003:00001377:00006012",
}


def find_post_swap_device(allowed_ids: set[str]) -> Path | None:
    matches = []
    for node in sorted(Path("/sys/class/hidraw").glob("hidraw*/device")):
        try:
            uevent = dict(line.split("=", 1) for line in (node / "uevent").read_text().splitlines())
            if (
                uevent.get("HID_ID") in allowed_ids
                and uevent.get("HID_PHYS", "").endswith("/input2")
                and (node / "report_descriptor").read_bytes() == EXPECTED
            ):
                matches.append(Path("/dev") / node.parent.name)
        except FileNotFoundError:
            continue
    if len(matches) > 1:
        raise ValueError(f"multiple post-swap interfaces: {matches}")
    return matches[0] if matches else None


def expect(value: bytes, opcode: int, length: int | None = None) -> None:
    if len(value) < 3 or value[0] != opcode:
        raise ValueError(f"expected opcode 0x{opcode:02x}, got {value.hex()}")
    if int.from_bytes(value[1:3], "big") != len(value) - 3:
        raise ValueError("malformed VM packet: " + value.hex())
    if length is not None and len(value) != length:
        raise ValueError("unexpected VM packet length: " + value.hex())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-capture", type=Path, required=True)
    parser.add_argument("--resume-capture", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=55)
    parser.add_argument("--hid-id", choices=("product", "charging", "either"), default="either")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    staged = json.loads(args.stage_capture.read_text())
    resumed = json.loads(args.resume_capture.read_text())
    if not (
        staged.get("completed") == "All pre-footer bytes accepted; footer and apply commands withheld"
        and staged.get("candidateSha256")
        and staged.get("sessionId")
        and "error" not in staged
        and resumed.get("candidateSha256") == staged.get("candidateSha256")
        and resumed.get("sessionId") == staged.get("sessionId")
        and resumed.get("newValue") == 2
        and resumed.get("preservedLastClosedPartition") == 10
        and resumed.get("readbackVerified") is True
        and resumed.get("resetRequested") is True
        and "error" not in resumed
    ):
        raise ValueError("stage/resume evidence guard failed")
    allowed_ids = {
        "product": {"0003:00001377:00006012"},
        "charging": {"0003:00000A12:00004007"},
        "either": POST_SWAP_HID_IDS,
    }[args.hid_id]
    guard = {
        "candidateSha256": staged["candidateSha256"],
        "sessionId": staged["sessionId"],
        "expectedUsbIds": sorted(allowed_ids),
        "handshake": [
            "SYNC_REQ 0x13 with candidate session id",
            "SYNC_CFM 0x14 must report resume=3 and protocol=3",
            "START_REQ 0x01 must return success and enter COMMIT_HOST_CONTINUE",
            "PROCEED_TO_COMMIT 0x0e action=0",
        ],
        "commitCfmOnlyIfRequested": True,
        "imageDataSent": False,
        "abortSent": False,
    }
    if not args.execute:
        print(json.dumps(guard, indent=2))
        return 0
    if args.output is None:
        parser.error("--output required with --execute")
    if args.output.exists():
        raise ValueError("capture already exists")
    result = dict(guard)
    result.update({"journal": [], "mutationAttempted": False, "commitCfmSent": False})
    with args.output.open("x+") as capture:
        def save() -> None:
            capture.seek(0)
            json.dump(result, capture, indent=2)
            capture.write("\n")
            capture.truncate()
            capture.flush()
            os.fsync(capture.fileno())

        # Preserve initial evidence even if the waiting process is interrupted.
        result["startedAtUnix"] = time.time()
        save()
        fd = None
        connected = False
        try:
            deadline = time.monotonic() + args.wait_seconds
            device = None
            last_permission_error = None
            while time.monotonic() < deadline:
                device = find_post_swap_device(allowed_ids)
                if device is not None:
                    try:
                        fd = os.open(device, os.O_RDWR | os.O_NONBLOCK)
                        break
                    except PermissionError as error:
                        last_permission_error = str(error)
                    except FileNotFoundError:
                        # USB re-enumeration can replace the hidraw node after
                        # discovery but before open. Rediscover it in the next
                        # iteration instead of losing the 60-second window.
                        device = None
                time.sleep(0.1)
            if fd is None:
                raise TimeoutError(
                    "post-swap HID did not become writable within window"
                    + (f": {last_permission_error}" if last_permission_error else "")
                )
            result["device"] = str(device)
            result["openedAtUnix"] = time.time()
            result["hidUevent"] = (Path('/sys/class/hidraw') / device.name / 'device/uevent').read_text()
            result["deviceWritableAtMonotonic"] = time.monotonic()
            save()
            transport_command(fd, 2, result["journal"])
            status = receive(fd, result["journal"], timeout=5)
            result["connectStatus"] = status.hex()
            if status not in (b"\0", b"\0\0"):
                raise RuntimeError("post-reboot transport rejected connection: " + status.hex())
            connected = True

            session_id = bytes.fromhex(staged["sessionId"])
            send_vm(fd, packet(0x13, session_id), result["journal"])
            sync = receive(fd, result["journal"], timeout=5)
            expect(sync, 0x14, 9)
            result["sync"] = sync.hex()
            if sync[3] != 3 or sync[4:8] != session_id or sync[8] != 3:
                raise ValueError("exact POST_REBOOT resume/session/protocol not confirmed")

            # SYNC always leaves the Qualcomm upgrade machine in READY. START
            # is required to resume point 3 and enter COMMIT_HOST_CONTINUE;
            # only that state accepts PROCEED_TO_COMMIT / IN_PROGRESS_RES.
            send_vm(fd, packet(0x01), result["journal"])
            started = receive(fd, result["journal"], timeout=5)
            expect(started, 0x02, 6)
            result["start"] = started.hex()
            if started[3] != 0:
                raise ValueError("START rejected; PROCEED_TO_COMMIT not sent")
            result["startConfirmed"] = True
            save()

            result["mutationAttempted"] = True
            save()
            send_vm(fd, packet(0x0E, b"\0"), result["journal"])
            result["proceedToCommitSent"] = True
            save()

            # Smart Control allows 60 seconds here. Application validation can
            # be asynchronous; PROCEED cancels the earlier reconnect timeout.
            protocol_deadline = time.monotonic() + 65
            while time.monotonic() < protocol_deadline:
                value = receive(fd, result["journal"], timeout=max(0.1, protocol_deadline - time.monotonic()))
                opcode = value[0]
                if opcode == 0x0F:
                    expect(value, 0x0F, 3)
                    if result["commitCfmSent"]:
                        raise ValueError("duplicate COMMIT_REQ")
                    send_vm(fd, packet(0x10, b"\0"), result["journal"])
                    result["commitReq"] = value.hex()
                    result["commitCfmSent"] = True
                    save()
                    continue
                if opcode == 0x12:
                    expect(value, 0x12, 3)
                    result["completeInd"] = value.hex()
                    result["completed"] = True
                    save()
                    break
                if opcode == 0x11:
                    expect(value, 0x11)
                    result["errorWarnInd"] = value.hex()
                    raise RuntimeError("upgrade error/warning during commit: " + value.hex())
                raise ValueError("unexpected post-reboot packet: " + value.hex())
            else:
                raise TimeoutError("no COMPLETE_IND within post-reboot protocol timeout")

            try:
                transport_command(fd, 7, result["journal"])
                result["disconnectSent"] = True
                connected = False
            except OSError as error:
                if error.errno not in (errno.EIO, errno.ENODEV):
                    raise
                result["deviceResetAfterCommit"] = True
                result["disconnectErrno"] = error.errno
                connected = False
        except Exception as error:
            result["error"] = str(error)
            if fd is not None and connected and not result.get("completed"):
                try:
                    transport_command(fd, 7, result["journal"])
                    result["safeDisconnectSent"] = True
                except Exception as disconnect_error:
                    result["disconnectError"] = str(disconnect_error)
        finally:
            if fd is not None:
                os.close(fd)
            save()
    print(json.dumps({key: value for key, value in result.items() if key != "journal"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
