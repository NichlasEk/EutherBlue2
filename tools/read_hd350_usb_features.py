#!/usr/bin/env python3
"""Read only the two declared HD350 vendor HID feature reports (IDs 3, 4).

Opens hidraw O_RDONLY. No output report, SET_REPORT, reset, or flash command.
Requires a matching USB ID, interface number and exact report descriptor.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path

EXPECTED = bytes.fromhex(
    '0600ff0901a101150026ff007508090296410085019102090296410085059102'
    '09029541850281020902950d85068102090295038503b102090295038504b102c0'
)


def read_features(device):
    if device.parent != Path('/dev') or not device.name.startswith('hidraw'):
        raise ValueError('expected /dev/hidrawN')
    sysdevice = Path('/sys/class/hidraw') / device.name / 'device'
    info = dict(line.split('=', 1) for line in (sysdevice / 'uevent').read_text().splitlines())
    if info.get('HID_ID') != '0003:00001377:00006012':
        raise ValueError('not USB HD350BT 1377:6012')
    if not info.get('HID_PHYS', '').endswith('/input2'):
        raise ValueError('not expected vendor interface 2')
    descriptor = (sysdevice / 'report_descriptor').read_bytes()
    if descriptor != EXPECTED:
        raise ValueError('report descriptor differs; do not probe')
    result = {'device': str(device), 'usbId': '1377:6012', 'interface': 2,
              'descriptorSha256': hashlib.sha256(descriptor).hexdigest(),
              'operation': 'HIDIOCGFEATURE only, O_RDONLY', 'reports': []}
    fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
    try:
        for report_id in (3, 4):
            # Linux _IOC(READ|WRITE, 'H', 0x07, 4): buffer contains ID + 3 bytes.
            # WRITE denotes userspace buffer direction, not HID SET_REPORT.
            buffer = bytearray([report_id, 0, 0, 0])
            try:
                returned = fcntl.ioctl(fd, 0xC0044807, buffer, True)
            except OSError as error:
                result['reports'].append({'id': report_id, 'errorNumber': error.errno,
                                          'error': error.strerror})
                continue
            if not 1 <= returned <= 4 or buffer[0] != report_id:
                raise ValueError('unexpected feature report response')
            result['reports'].append({'id': report_id, 'length': returned,
                                      'hex': buffer[:returned].hex()})
    finally:
        os.close(fd)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('device', type=Path)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    result = read_features(args.device)
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as f:
            f.write(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
