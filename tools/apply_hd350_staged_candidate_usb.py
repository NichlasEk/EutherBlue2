#!/usr/bin/env python3
"""Apply the pinned staged HD 350BT bank through the verified resume-2 path.

Requires the completed pre-footer staging capture and exact resume-context
readback. Sends no image data, footer, abort, erase, or commit. It sends one
standard TRANSFER_COMPLETE_RES(action=0); the headset then owns swap/reboot.
"""
import argparse
import errno
import json
import os
from pathlib import Path
import select
import time

from stage_hd350_unsigned_candidate_usb import (
    FOOTER_OFFSET, identify, packet, receive, send_vm, transport_command,
)


def evidence_guard(stage_capture, resume_capture):
    staged = json.loads(stage_capture.read_text())
    resumed = json.loads(resume_capture.read_text())
    if not (staged.get('completed') == 'All pre-footer bytes accepted; footer and apply commands withheld'
            and staged.get('bytesSent') == FOOTER_OFFSET
            and staged.get('fileCursor') == FOOTER_OFFSET
            and staged.get('stoppedAtFooterRequest') is True
            and staged.get('footerSent') is False
            and staged.get('bankSwapRequested') is False
            and 'error' not in staged):
        raise ValueError('completed staging evidence guard failed')
    resume_context_sha = (resumed.get('modifiedContextSha256')
                          or resumed.get('resume2ContextSha256'))
    if not (resumed.get('candidateSha256') == staged.get('candidateSha256')
            and resumed.get('sessionId') == staged.get('sessionId')
            and isinstance(resume_context_sha, str)
            and len(resume_context_sha) == 64
            and resumed.get('changedWord') == 13
            and resumed.get('newValue') == 2
            and resumed.get('preservedLastClosedPartition') == 10
            and resumed.get('readbackVerified') is True
            and resumed.get('resetRequested') is True
            and 'error' not in resumed):
        raise ValueError('resume-2 evidence guard failed')
    return (staged['candidateSha256'], bytes.fromhex(staged['sessionId']),
            resume_context_sha)


def expect(value, opcode, length=None):
    if len(value) < 3 or value[0] != opcode:
        raise ValueError(f'expected opcode 0x{opcode:02x}, got {value.hex()}')
    if int.from_bytes(value[1:3], 'big') != len(value) - 3:
        raise ValueError('malformed VM packet: ' + value.hex())
    if length is not None and len(value) != length:
        raise ValueError('unexpected VM packet length: ' + value.hex())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    parser.add_argument('--stage-capture', type=Path, required=True)
    parser.add_argument('--resume-capture', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    expected_sha, session_id, resume_context_sha = evidence_guard(
        args.stage_capture, args.resume_capture)
    identify(args.device)
    guard = {
        'candidateSha256': expected_sha,
        'stagedBytes': FOOTER_OFFSET,
        'resumeContextSha256': resume_context_sha,
        'sessionId': session_id.hex(),
        'stageCapture': str(args.stage_capture),
        'resumeCapture': str(args.resume_capture),
        'transferCompleteResponsesPlanned': 1,
        'footerSent': False,
        'imageDataSent': False,
        'commitSent': False,
        'abortSent': False,
        'bankSwapRequested': False,
    }
    if not args.execute:
        print(json.dumps(guard, indent=2))
        return
    if args.output is None:
        parser.error('--output required with --execute')
    if args.output.exists():
        raise ValueError('capture already exists')

    result = dict(guard)
    result.update({'device': str(args.device), 'journal': [], 'mutationAttempted': False})
    with args.output.open('x+') as capture:
        def save():
            capture.seek(0)
            json.dump(result, capture, indent=2)
            capture.write('\n')
            capture.truncate()
            capture.flush()
            os.fsync(capture.fileno())

        fd = None
        connected = False
        try:
            fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
            transport_command(fd, 2, result['journal'])
            status = receive(fd, result['journal'])
            result['connectStatus'] = status.hex()
            if status not in (b'\0', b'\0\0'):
                raise RuntimeError('USB transport rejected connection: ' + status.hex())
            connected = True

            send_vm(fd, packet(0x19), result['journal'])
            version = receive(fd, result['journal'])
            expect(version, 0x1a)
            result['upgradeVersion'] = version.hex()
            if version[3:] != bytes.fromhex('000100000001'):
                raise ValueError('unexpected upgrade protocol version')

            send_vm(fd, packet(0x13, session_id), result['journal'])
            sync = receive(fd, result['journal'])
            expect(sync, 0x14, 9)
            result['sync'] = sync.hex()
            save()
            if sync[3] != 2 or sync[4:8] != session_id or sync[8] != 3:
                raise ValueError('resume point 2/session/protocol not confirmed; no apply')

            send_vm(fd, packet(0x01), result['journal'])
            started = receive(fd, result['journal'])
            expect(started, 0x02, 6)
            result['start'] = started.hex()
            save()
            if started[3] != 0:
                raise ValueError('START rejected; no apply')

            send_vm(fd, packet(0x16), result['journal'])
            complete = receive(fd, result['journal'], timeout=20)
            expect(complete, 0x0b, 3)
            result['transferCompleteInd'] = complete.hex()
            save()

            # The sole irreversible trigger in this tool. The stock sink app
            # responds internally to UPGRADE_APPLY_IND and performs the swap.
            result['mutationAttempted'] = True
            result['bankSwapRequested'] = True
            save()
            send_vm(fd, packet(0x0c, b'\0'), result['journal'])
            result['transferCompleteResponsesSent'] = 1
            save()

            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                if not select.select([fd], [], [], min(1, deadline - time.monotonic()))[0]:
                    continue
                try:
                    report = os.read(fd, 256)
                    result['journal'].append({'direction': 'in-after-apply', 'report': report.hex()})
                    if not report:
                        result['usbDisconnectedAfterApply'] = True
                        break
                except OSError as error:
                    if error.errno in (errno.EIO, errno.ENODEV):
                        result['usbDisconnectedAfterApply'] = True
                        result['disconnectErrno'] = error.errno
                        break
                    raise
            else:
                result['usbDisconnectObserved'] = False
            connected = False  # Never send a transport command after apply.
        except Exception as error:
            result['error'] = str(error)
            if fd is not None and connected and not result['bankSwapRequested']:
                try:
                    transport_command(fd, 7, result['journal'])
                    result['safeDisconnectSent'] = True
                except Exception as disconnect_error:
                    result['disconnectError'] = str(disconnect_error)
        finally:
            if fd is not None:
                os.close(fd)
            save()
    print(json.dumps({key: value for key, value in result.items() if key != 'journal'}, indent=2))


if __name__ == '__main__':
    main()
