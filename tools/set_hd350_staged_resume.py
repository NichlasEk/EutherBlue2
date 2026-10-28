#!/usr/bin/env python3
"""Set only resume word 13 of the exact staged HD 350BT context to PRE_REBOOT=2.

The tool is pinned to the captured 19-word context and refuses every other
input.  It neither transfers image data nor sends footer, abort, commit,
transfer-complete, erase, or bank-swap commands.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket

from read_hd350_gaia_file import Gaia
from probe_hd350_hidden_usb_audio import check_stock


EXPECTED_CONTEXT = bytes.fromhex(
    '00000001000000010000000000010001000100020000197326db0000000a0000000000000000')
EXPECTED_SHA256 = '6c4843e6c296eb2a0f0d7785e2e64e7c80988138f621ea3bd811fd997121f171'
RESUME_WORD = 13
LAST_CLOSED_WORD = 14


def changed_context():
    words = [int.from_bytes(EXPECTED_CONTEXT[i:i + 2], 'big')
             for i in range(0, len(EXPECTED_CONTEXT), 2)]
    if (len(words) != 19 or words[11:13] != [0x1973, 0x26db]
            or words[RESUME_WORD] != 0 or words[LAST_CLOSED_WORD] != 10):
        raise ValueError('pinned context structure guard failed')
    words[RESUME_WORD] = 2
    return b''.join(word.to_bytes(2, 'big') for word in words)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--channel', type=int)
    args = parser.parse_args()
    check_stock()
    modified = changed_context()
    if hashlib.sha256(EXPECTED_CONTEXT).hexdigest() != EXPECTED_SHA256:
        raise ValueError('pinned context hash mismatch')
    guard = {
        'expectedContextSha256': EXPECTED_SHA256,
        'modifiedContextSha256': hashlib.sha256(modified).hexdigest(),
        'changedWord': RESUME_WORD,
        'oldValue': 0,
        'newValue': 2,
        'preservedLastClosedPartition': 10,
        'forbiddenUpgradeOpcodes': [0x04, 0x07, 0x0c, 0x0f, 0x15],
        'imageDataSent': False,
        'bankSwapRequested': False,
    }
    if not args.execute:
        print(json.dumps(guard, indent=2))
        return
    if args.output is None:
        parser.error('--output required with --execute')
    if args.channel is None or not 1 <= args.channel <= 30:
        parser.error('--channel 1..30 required with --execute')
    if args.output.exists():
        raise ValueError('capture already exists')

    result = dict(guard)
    result.update({'transactions': [], 'replies': {}, 'mutationAttempted': False})
    with args.output.open('x+') as capture:
        def save():
            capture.seek(0)
            json.dump(result, capture, indent=2)
            capture.write('\n')
            capture.truncate()
            capture.flush()
            os.fsync(capture.fileno())

        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(8)
        gaia = Gaia(sock, result['transactions'])

        def query(name, command, payload=b'', vendor=10):
            reply = gaia.query(vendor, command, payload)
            result['replies'][name] = reply.hex()
            save()
            return reply

        def success(name, command, payload=b''):
            reply = query(name, command, payload)
            if reply != b'\0':
                raise ValueError(name + ' rejected: ' + reply.hex())

        try:
            result['rfcommChannel'] = args.channel
            save()
            sock.connect(('00:00:00:00:00:00', args.channel))
            if query('version', 0x280, vendor=0x494) != bytes.fromhex('00000500050000'):
                raise ValueError('expected product firmware 5.5.0 not confirmed')
            if query('bootMode', 0x282) != b'\0\0':
                raise ValueError('headset not in normal boot mode')
            before = query('contextBefore', 0x710, b'\0\4')
            if before != b'\0\0\4' + EXPECTED_CONTEXT:
                raise ValueError('live context differs from pinned staged context; no write')
            result['mutationAttempted'] = True
            save()
            # The matched GAIA handler converts protocol bytes to words using
            # half the post-key payload length; matching padding is required.
            payload = b'\0\4' + modified + b'\0' * 36
            success('storeResume2Context', 0x712, payload)
            after = query('contextAfter', 0x710, b'\0\4')
            if after != b'\0\0\4' + modified:
                raise ValueError('resume2 context readback mismatch; no reset')
            result['readbackVerified'] = True
            save()
            success('resetToReloadResume2', 0x202, b'\0')
            result['resetRequested'] = True
        except Exception as error:
            result['error'] = str(error)
        finally:
            sock.close()
            save()
    print(json.dumps({key: value for key, value in result.items() if key != 'transactions'}, indent=2))


if __name__ == '__main__':
    main()
