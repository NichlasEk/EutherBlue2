#!/usr/bin/env python3
"""Re-arm exact staged HD 350BT context from POST_REBOOT=3 to PRE_REBOOT=2."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket

from read_hd350_gaia_file import Gaia
from probe_hd350_hidden_usb_audio import check_stock


EXPECTED = bytes.fromhex(
    '00000001000000010000000000010001000100020000197326db0003000a0000000000000000')
EXPECTED_SHA = '5df290ded6e612864a03544155bf6571c005e282fbb41fbd3c4cabc6dcb15607'


def modified_context():
    words = [int.from_bytes(EXPECTED[i:i + 2], 'big') for i in range(0, len(EXPECTED), 2)]
    if (len(words) != 19 or words[11:13] != [0x1973, 0x26db]
            or words[13] != 3 or words[14] != 10):
        raise ValueError('pinned post-reboot context guard failed')
    words[13] = 2
    return b''.join(word.to_bytes(2, 'big') for word in words)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--channel', type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    check_stock()
    modified = modified_context()
    if hashlib.sha256(EXPECTED).hexdigest() != EXPECTED_SHA:
        raise ValueError('pinned context hash mismatch')
    guard = {
        'expectedResume3ContextSha256': EXPECTED_SHA,
        'resume2ContextSha256': hashlib.sha256(modified).hexdigest(),
        'changedWord': 13, 'oldValue': 3, 'newValue': 2,
        'preservedLastClosedPartition': 10,
        'imageDataSent': False, 'footerSent': False,
        'bankSwapRequested': False,
    }
    if not args.execute:
        print(json.dumps(guard, indent=2))
        return
    if args.output is None or args.channel is None or not 1 <= args.channel <= 30:
        parser.error('--output and --channel 1..30 required with --execute')
    if args.output.exists():
        raise ValueError('capture already exists')

    result = dict(guard)
    result.update({'rfcommChannel': args.channel, 'transactions': [],
                   'replies': {}, 'mutationAttempted': False})
    with args.output.open('x+') as capture:
        def save():
            capture.seek(0); json.dump(result, capture, indent=2); capture.write('\n')
            capture.truncate(); capture.flush(); os.fsync(capture.fileno())

        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(8)
        gaia = Gaia(sock, result['transactions'])
        def query(name, command, payload=b'', vendor=10):
            reply = gaia.query(vendor, command, payload)
            result['replies'][name] = reply.hex(); save(); return reply
        def success(name, command, payload=b''):
            reply = query(name, command, payload)
            if reply != b'\0': raise ValueError(name + ' rejected: ' + reply.hex())
        try:
            sock.connect(('00:00:00:00:00:00', args.channel))
            if query('version', 0x280, vendor=0x494) != bytes.fromhex('00000500050000'):
                raise ValueError('firmware 5.5.0 not confirmed')
            if query('bootMode', 0x282) != b'\0\0':
                raise ValueError('not normal boot mode')
            if query('contextBefore', 0x710, b'\0\4') != b'\0\0\4' + EXPECTED:
                raise ValueError('live context differs from pinned resume-3 context; no write')
            result['mutationAttempted'] = True; save()
            success('storeResume2Context', 0x712, b'\0\4' + modified + b'\0' * 36)
            if query('contextAfter', 0x710, b'\0\4') != b'\0\0\4' + modified:
                raise ValueError('resume-2 readback mismatch; no reset')
            result['readbackVerified'] = True; save()
            success('resetToReloadResume2', 0x202, b'\0')
            result['resetRequested'] = True
        except Exception as error:
            result['error'] = str(error)
        finally:
            sock.close(); save()
    print(json.dumps({k: v for k, v in result.items() if k != 'transactions'}, indent=2))


if __name__ == '__main__':
    main()
