#!/usr/bin/env python3
"""Fixed key201 one-word experiment, with exact original-value restoration.

PS_SIZE_ADJ in the matched GAIA handler halves the protocol word count again
on this octet-addressed target. Restore uses padding to request two PS words;
readback is mandatory before reset. No general key/value interface.
"""
import argparse
import json
import os
from pathlib import Path
import socket
from read_hd350_gaia_file import Gaia
from probe_hd350_hidden_usb_audio import check_stock


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--action', choices=('enter', 'restore'), required=True)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    check_stock()
    enter = a.action == 'enter'
    payload = bytes.fromhex('00c900aa' if enter else '00c9ffff001c0000')
    expected = bytes.fromhex('0000c900aa' if enter else '0000c9ffff001c')
    if not a.execute:
        print('Dry-run:', a.action, 'key201 payload', payload.hex(), 'then verified reset', 2 if enter else 0)
        return
    if a.output is None:
        ap.error('--output required')
    r = {'action': a.action, 'transactions': [], 'replies': {}, 'writeAttempted': False, 'resetAttempted': False}
    with a.output.open('x') as f:
        def save():
            f.seek(0); json.dump(r, f, indent=2); f.write('\n'); f.truncate()
            f.flush(); os.fsync(f.fileno())
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(5)
        try:
            s.connect(('00:00:00:00:00:00', 1)); g = Gaia(s, r['transactions'])
            def query(name, command, data=b'', vendor=10):
                v = g.query(vendor, command, data)
                r['replies'][name] = v.hex(); save(); return v
            if query('version', 0x280, vendor=0x494) != bytes.fromhex('00000500050000'):
                raise ValueError('Wrong firmware')
            mode = query('mode', 0x282)
            if mode not in (b'\0\0', b'\0\2'):
                raise ValueError('Unexpected boot mode')
            prior = query('keyBefore', 0x710, bytes.fromhex('00c9'))
            if enter and prior != bytes.fromhex('0000c9ffff001c'):
                raise ValueError('Original key does not match backup')
            if not enter and (len(prior) not in (5, 7) or prior[:3] != bytes.fromhex('0000c9')):
                raise ValueError('Unexpected key reply')
            if prior != expected:
                r['writeAttempted'] = True; save()
                if query('store', 0x712, payload) != b'\0':
                    raise ValueError('Store rejected; no reset sent')
                if query('keyAfter', 0x710, bytes.fromhex('00c9')) != expected:
                    raise ValueError('Readback mismatch; no reset sent; inspect journal')
            if not enter and mode == b'\0\0':
                query('versionAfterRestore', 0x280, vendor=0x494)
                r['status'] = 'Original key verified; already in normal boot mode; no reset needed'
            else:
                r['resetAttempted'] = True; save()
                query('reset', 0x202, bytes((2 if enter else 0,)))
        except Exception as e:
            r['error'] = str(e)
        finally:
            s.close(); save()
    print(json.dumps({k:v for k,v in r.items() if k != 'transactions'}, indent=2))


if __name__ == '__main__':
    main()
