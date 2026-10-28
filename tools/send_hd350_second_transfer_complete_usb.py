#!/usr/bin/env python3
"""Send one second TRANSFER_COMPLETE_RES to the still-connected HD 350BT session."""
import argparse
import errno
import json
import os
from pathlib import Path
import select
import time

from stage_hd350_unsigned_candidate_usb import identify, packet, receive, send_vm, transport_command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    parser.add_argument('--apply-capture', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    prior = json.loads(args.apply_capture.read_text())
    session_id = prior.get('sessionId', '')
    expected_sync = '14000602' + session_id + '03'
    if not (len(session_id) == 8
            and prior.get('sync') == expected_sync
            and prior.get('transferCompleteInd') == '0b0000'
            and prior.get('transferCompleteResponsesSent') == 1
            and prior.get('bankSwapRequested') is True
            and prior.get('usbDisconnectObserved') is False
            and 'error' not in prior):
        raise ValueError('first apply evidence guard failed')
    identify(args.device)
    guard = {'priorTransferCompleteResponses': 1,
             'candidateSha256': prior.get('candidateSha256'),
             'sessionId': session_id,
             'applyCapture': str(args.apply_capture),
             'secondTransferCompleteResponsePlanned': True,
             'requiredTransportStatus': '02',
             'packet': '0c000100',
             'footerSent': False, 'imageDataSent': False, 'commitSent': False,
             'bankSwapRequested': False}
    if not args.execute:
        print(json.dumps(guard, indent=2)); return
    if args.output is None:
        parser.error('--output required with --execute')
    if args.output.exists():
        raise ValueError('capture already exists')
    result = dict(guard)
    result.update({'device': str(args.device), 'journal': [], 'mutationAttempted': False})
    with args.output.open('x+') as capture:
        def save():
            capture.seek(0); json.dump(result, capture, indent=2); capture.write('\n')
            capture.truncate(); capture.flush(); os.fsync(capture.fileno())
        fd = None
        try:
            fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
            transport_command(fd, 2, result['journal'])
            status = receive(fd, result['journal'])
            result['connectStatus'] = status.hex(); save()
            if status != b'\x02':
                raise ValueError('existing apply transport not confirmed; no second response')
            result['mutationAttempted'] = True
            result['bankSwapRequested'] = True
            save()
            send_vm(fd, packet(0x0c, b'\0'), result['journal'])
            result['secondTransferCompleteResponseSent'] = True; save()
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if not select.select([fd], [], [], min(1, deadline-time.monotonic()))[0]:
                    continue
                try:
                    report = os.read(fd, 256)
                    result['journal'].append({'direction': 'in-after-second-apply',
                                              'report': report.hex()})
                    if not report:
                        result['usbDisconnectedAfterSecondApply'] = True; break
                except OSError as error:
                    if error.errno in (errno.EIO, errno.ENODEV):
                        result['usbDisconnectedAfterSecondApply'] = True
                        result['disconnectErrno'] = error.errno; break
                    raise
            else:
                result['usbDisconnectObserved'] = False
        except Exception as error:
            result['error'] = str(error)
        finally:
            if fd is not None: os.close(fd)
            save()
    print(json.dumps({k: v for k, v in result.items() if k != 'journal'}, indent=2))


if __name__ == '__main__':
    main()
