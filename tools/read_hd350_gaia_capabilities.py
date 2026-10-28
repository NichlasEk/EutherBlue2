#!/usr/bin/env python3
"""Fixed read-only GAIA capability checks, all in one RFCOMM session.

No feature setters, PS stores, reset, partition opens, or upgrade commands.
"""
import argparse
import json
from pathlib import Path
import socket
from read_hd350_gaia_file import Gaia

QUERIES = (
    ('productVersion', 0x0494, 0x0280, b''),
    ('apiVersion', 0x000a, 0x0300, b''),
    ('bootMode', 0x000a, 0x0282, b''),
    ('debugNoOperation', 0x000a, 0x0700, b''),
    ('memorySlots', 0x000a, 0x0730, b''),
    # 0258 is only a probe key; ADK6.4 defines PSKEY_USR0 as650 (028a).
    ('retrieveKey0258', 0x000a, 0x0710, bytes.fromhex('0258')),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'address': '00:00:00:00:00:00', 'transactions': [], 'replies': {}}
    with args.output.open('x') as capture:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(5)
        try:
            sock.connect((result['address'], 1))
            gaia = Gaia(sock, result['transactions'])
            for name, vendor, command, payload in QUERIES:
                reply = gaia.query(vendor, command, payload)
                result['replies'][name] = reply.hex()
                if name == 'productVersion' and reply != bytes.fromhex('00000500050000'):
                    raise ValueError('Expected firmware5.5.0 not confirmed')
        except Exception as error:
            result['error'] = str(error)
        finally:
            sock.close()
            json.dump(result, capture, indent=2); capture.write('\n')
            print(json.dumps({'replies': {k: {'status': bytes.fromhex(v)[0],
                                             'payloadBytes': len(bytes.fromhex(v))-1}
                                         for k,v in result['replies'].items()},
                              'error': result.get('error')}, indent=2))


if __name__ == '__main__':
    main()
