#!/usr/bin/env python3
"""One firmware-derived service-mode request. Dry-run unless --enter is given.

This IS a persistent mode change: stock handler stores key201 and calls
BootSetMode(2). It is not a flash unlock. Normal-mode recovery via GAIA0202/00
is statically identified, but has not been tested from this hidden mode.
No opcode sweep, flash data, automatic retries, or automatic recovery.
"""
from local_device import service_address_bytes
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import time

from listen_hd350_vendor_usb import EXPECTED
from probe_hd350_usb_debug_event import STOCK, usb_inventory

PACKET = bytes.fromhex('10883d').ljust(32, b'\0')


def check_stock():
    data = STOCK.read_bytes()
    if hashlib.sha256(data).hexdigest() != '25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48':
        raise ValueError('Stock image mismatch')
    for offset, expected in ((0x1235ca, '483f'), (0x1235da, '02f0c940'),
                             (0x1235e2, '8220'), (0x1232ba, '89c8')):
        expected = bytes.fromhex(expected)
        if data[offset:offset+len(expected)] != expected:
            raise ValueError('Service branch mismatch')


def identity(fd, command):
    packet = bytes((0x10, 0x88, command)).ljust(32, b'\0')
    if os.write(fd, packet) != 32:
        raise RuntimeError('Short identity write')
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if not select.select([fd], [], [], max(0, deadline-time.monotonic()))[0]:
            break
        response = os.read(fd, 256)
        if len(response) == 32 and response[:3] == packet[:3]:
            return response
    raise RuntimeError('Identity response missing; mode command not sent')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enter', action='store_true')
    ap.add_argument('--device', type=Path)
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    check_stock()
    if not args.enter:
        print('Offline guards passed. Prepared one service command10883d; no device opened.')
        return
    if args.device is None or args.output is None:
        ap.error('--enter requires --device and --output')
    if args.device.parent != Path('/dev') or not args.device.name.startswith('hidraw'):
        raise ValueError('Expected /dev/hidrawN')
    node = Path('/sys/class/hidraw') / args.device.name / 'device'
    info = dict(line.split('=', 1) for line in (node/'uevent').read_text().splitlines())
    if (info.get('HID_ID') != '0003:00001377:00006012'
            or not info.get('HID_PHYS', '').endswith('/input0')
            or (node/'report_descriptor').read_bytes() != EXPECTED):
        raise ValueError('Wrong device or descriptor')
    result = {'device': str(args.device), 'request': PACKET.hex(),
              'modeWriteAttempted': False, 'usbBefore': usb_inventory()}
    fd = None
    with args.output.open('x') as capture:
        def save():
            capture.seek(0)
            json.dump(result, capture, indent=2)
            capture.write('\n')
            capture.truncate()
            capture.flush()
            os.fsync(capture.fileno())
        try:
            fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
            version = identity(fd, 0x1c)
            address = identity(fd, 0x19)
            result['versionReply'] = version.hex()
            result['addressReply'] = address.hex()
            if version[8:11] != b'550' or address[3:9] != service_address_bytes():
                raise ValueError('Expected firmware/address not confirmed')
            result['modeWriteAttempted'] = True
            save()  # Journal before the one mutation; interrupted write is unknown.
            result['writtenBytes'] = os.write(fd, PACKET)
            if result['writtenBytes'] != 32:
                raise RuntimeError('Short mode write; do not retry')
            save()
            os.close(fd)
            fd = None
            result['observations'] = []
            for seconds in range(2, 21, 2):
                time.sleep(2)
                result['observations'].append({'seconds': seconds, 'usb': usb_inventory()})
            result['usbAfter'] = usb_inventory()
        except Exception as error:
            result['error'] = str(error)
        finally:
            if fd is not None:
                os.close(fd)
            save()
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ('usbBefore', 'usbAfter', 'observations')}, indent=2))


if __name__ == '__main__':
    main()
