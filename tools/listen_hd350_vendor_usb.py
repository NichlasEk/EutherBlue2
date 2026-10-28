#!/usr/bin/env python3
"""Listen for HD350 interface 0 input reports for five seconds; send nothing."""
import argparse
import json
import os
from pathlib import Path
import select
import time

EXPECTED = bytes.fromhex(
    '06a0ff0901a10185100901150026ff007508951f910009027508951f8100c0'
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('capture already exists')
    if args.device.parent != Path('/dev') or not args.device.name.startswith('hidraw'):
        raise ValueError('expected /dev/hidrawN')
    sysdev = Path('/sys/class/hidraw') / args.device.name / 'device'
    info = dict(line.split('=', 1) for line in (sysdev / 'uevent').read_text().splitlines())
    if (info.get('HID_ID') != '0003:00001377:00006012'
            or not info.get('HID_PHYS', '').endswith('/input0')
            or (sysdev / 'report_descriptor').read_bytes() != EXPECTED):
        raise ValueError('device identity or descriptor mismatch')
    result = {'device': str(args.device), 'interface': 0,
              'operation': 'O_RDONLY passive input, no ioctl or output', 'reports': []}
    try:
        fd = os.open(args.device, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as error:
        result.update(errorNumber=error.errno, error=error.strerror)
    else:
        try:
            deadline = time.monotonic() + 5
            while len(result['reports']) < 64:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                    break
                data = os.read(fd, 256)
                if not data:
                    break
                result['reports'].append(data.hex())
        finally:
            os.close(fd)
    encoded = json.dumps(result, indent=2) + '\n'
    with args.output.open('x') as out:
        out.write(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
