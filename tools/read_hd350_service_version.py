#!/usr/bin/env python3
"""Single firmware-derived HD350 report-16 identity probe; no opcode sweep.

Version: command 0x1c (hardware answered); address: candidate command 0x19.
Protocol interpretation is experimental. No reset, mode, or firmware packets.
"""
import argparse
import json
import os
from pathlib import Path
import select
import time
from listen_hd350_vendor_usb import EXPECTED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    parser.add_argument('--query', choices=('version', 'address'), default='version')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('capture exists')
    if args.device.parent != Path('/dev') or not args.device.name.startswith('hidraw'):
        raise ValueError('expected /dev/hidrawN')
    p = Path('/sys/class/hidraw') / args.device.name / 'device'
    info = dict(line.split('=', 1) for line in (p/'uevent').read_text().splitlines())
    if (info.get('HID_ID') != '0003:00001377:00006012'
            or not info.get('HID_PHYS', '').endswith('/input0')
            or (p/'report_descriptor').read_bytes() != EXPECTED):
        raise ValueError('identity or report descriptor mismatch')
    command = {'version': 0x1c, 'address': 0x19}[args.query]
    request = bytes([0x10, 0x88, command]).ljust(32, b'\0')
    result = {'device': str(args.device), 'interface': 0,
              'query': args.query, 'requestHex': request.hex(), 'sent': False, 'reports': []}
    fd = None
    try:
        fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
        written = os.write(fd, request)
        result['writtenBytes'] = written
        if written != len(request):
            raise RuntimeError('short write; no retry')
        result['sent'] = True
        deadline = time.monotonic() + 5
        while len(result['reports']) < 32:
            remaining = deadline-time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                break
            data = os.read(fd, 256)
            if not data:
                break
            result['reports'].append(data.hex())
            if len(data) == 32 and data.startswith(request[:3]):
                result['identityReply'] = data.hex()
                break
    except OSError as error:
        result.update(errorNumber=error.errno, error=str(error))
    finally:
        if fd is not None:
            os.close(fd)
        with args.output.open('x') as out:
            json.dump(result, out, indent=2)
            out.write('\n')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
