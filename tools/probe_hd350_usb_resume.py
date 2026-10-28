#!/usr/bin/env python3
"""Read HD 350BT USB upgrade resume state; never send START or DATA."""
import argparse
import json
import os
from pathlib import Path

from stage_hd350_unsigned_candidate_usb import (
    identify, packet, receive, send_vm, transport_command,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    parser.add_argument('--session-id', required=True,
                        help='exact four-byte upgrade file identifier')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    session_id = bytes.fromhex(args.session_id)
    if len(session_id) != 4:
        raise ValueError('--session-id must encode exactly four bytes')
    if args.output.exists():
        raise ValueError('capture already exists')
    identify(args.device)
    result = {'device': str(args.device), 'sessionId': session_id.hex(),
              'journal': [], 'startSent': False, 'dataSent': False}
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
        send_vm(fd, packet(0x13, session_id), result['journal'])
        sync = receive(fd, result['journal'])
        result['sync'] = sync.hex()
        if len(sync) != 9 or sync[0:3] != b'\x14\x00\x06' or sync[4:8] != session_id:
            raise ValueError('unexpected SYNC response: ' + sync.hex())
        result['resumePoint'] = sync[3]
        result['protocolVersion'] = sync[8]
    except Exception as error:
        result['error'] = str(error)
    finally:
        if fd is not None:
            if connected:
                try:
                    transport_command(fd, 7, result['journal'])
                    result['disconnectSent'] = True
                except Exception as error:
                    result['disconnectError'] = str(error)
            os.close(fd)
        with args.output.open('x') as capture:
            json.dump(result, capture, indent=2)
            capture.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
