#!/usr/bin/env python3
"""Request interface 0 input report 16 once using HIDIOCGINPUT, O_RDONLY."""
import argparse
import fcntl
import json
import os
from pathlib import Path
from listen_hd350_vendor_usb import EXPECTED


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
        raise ValueError('identity or descriptor mismatch')
    result = {'device': str(args.device), 'interface': 0, 'reportId': 16,
              'operation': 'HIDIOCGINPUT(32), one GET_REPORT, O_RDONLY'}
    fd = os.open(args.device, os.O_RDONLY | os.O_NONBLOCK)
    try:
        buffer = bytearray([16] + [0] * 31)
        try:
            # _IOC(READ|WRITE, 'H', 0x0a, 32); not SET_REPORT.
            count = fcntl.ioctl(fd, 0xC020480A, buffer, True)
            result.update(length=count, hex=buffer[:count].hex(),
                          validReport=1 <= count <= 32 and buffer[0] == 16)
        except OSError as error:
            result.update(errorNumber=error.errno, error=error.strerror)
    finally:
        os.close(fd)
    encoded = json.dumps(result, indent=2) + '\n'
    with args.output.open('x') as out:
        out.write(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
