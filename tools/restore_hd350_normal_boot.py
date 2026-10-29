#!/usr/bin/env python3
"""Fixed GAIA reset to bootmode0, only from confirmed HD350 firmware5.5/mode2.

Does not restore PS contents or write firmware. It needs live RFCOMM access;
the existence of this tool is not proof of recovery from hidden USB mode.
"""
from local_device import bluetooth_address
import argparse
import json
from pathlib import Path
import socket

from read_hd350_gaia_file import Gaia


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--restore-normal-boot', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    if not args.restore_normal_boot:
        print('Dry-run: version, bootmode and key201 reads, then0202 payload00 only if mode2.')
        return
    if args.output is None:
        ap.error('--output required')
    result = {'transactions': [], 'resetAttempted': False}
    with args.output.open('x') as capture:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(5)
        try:
            sock.connect((bluetooth_address(), 1))
            gaia = Gaia(sock, result['transactions'])
            version = gaia.query(0x0494, 0x0280)
            result['version'] = version.hex()
            if version != bytes.fromhex('00000500050000'):
                raise ValueError('Expected firmware not confirmed')
            mode = gaia.query(0x000a, 0x0282)
            result['bootMode'] = mode.hex()
            result['key201'] = gaia.query(0x000a, 0x0710, bytes.fromhex('00c9')).hex()
            if mode == b'\0\0':
                result['status'] = 'Already in normal boot mode; no reset sent'
            elif mode == b'\0\2':
                result['resetAttempted'] = True
                capture.write(json.dumps(result, indent=2)); capture.flush()
                result['resetReply'] = gaia.query(0x000a, 0x0202, b'\0').hex()
                result['status'] = 'Reset requested; subsequent device verification required'
            else:
                raise ValueError('Unexpected mode; no reset sent')
        except Exception as error:
            result['error'] = str(error)
        finally:
            sock.close()
            capture.seek(0); json.dump(result, capture, indent=2)
            capture.write('\n'); capture.truncate()
    print(json.dumps({k:v for k,v in result.items() if k != 'transactions'}, indent=2))


if __name__ == '__main__':
    main()
