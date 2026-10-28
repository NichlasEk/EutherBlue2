#!/usr/bin/env python3
"""Read HD 350BT ConfigStore upgrade context key 4; never mutate it."""
import argparse
import json
from pathlib import Path
import socket

from read_hd350_gaia_file import Gaia
from probe_hd350_hidden_usb_audio import check_stock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--channel', type=int, default=1)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('capture already exists')
    check_stock()
    result = {'transactions': [], 'replies': {}, 'mutationAttempted': False}
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.settimeout(8)
    gaia = Gaia(sock, result['transactions'])
    try:
        if not 1 <= args.channel <= 30:
            raise ValueError('RFCOMM channel must be 1..30')
        result['rfcommChannel'] = args.channel
        sock.connect(('00:00:00:00:00:00', args.channel))
        for name, vendor, command, payload in (
                ('version', 0x494, 0x280, b''),
                ('bootMode', 10, 0x282, b''),
                ('upgradeContextKey4', 10, 0x710, b'\0\4')):
            result['replies'][name] = gaia.query(vendor, command, payload).hex()
        if result['replies']['version'] != '00000500050000':
            raise ValueError('expected product firmware 5.5.0 not confirmed')
        if result['replies']['bootMode'] != '0000':
            raise ValueError('headset not in normal boot mode')
        raw = bytes.fromhex(result['replies']['upgradeContextKey4'])
        if raw == b'\5':
            result['contextPresent'] = False
        elif len(raw) >= 5 and raw[:3] == b'\0\0\4' and not (len(raw) - 3) % 2:
            result['contextPresent'] = True
            result['contextHex'] = raw[3:].hex()
            result['contextWords'] = [int.from_bytes(raw[i:i + 2], 'big')
                                      for i in range(3, len(raw), 2)]
            result['resumeWordIndex13'] = result['contextWords'][13]
            result['lastClosedPartitionWordIndex14'] = result['contextWords'][14]
        else:
            raise ValueError('unexpected key4 response: ' + raw.hex())
    except Exception as error:
        result['error'] = str(error)
    finally:
        sock.close()
        with args.output.open('x') as capture:
            json.dump(result, capture, indent=2)
            capture.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'transactions'}, indent=2))


if __name__ == '__main__':
    main()
