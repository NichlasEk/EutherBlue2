#!/usr/bin/env python3
"""Bounded HD350 AHI USB session: identity and two prompt config GETs only.

Uses HID output report 1 for requests, not the firmware transfer report.
No mode changes, configuration writes, reset, or upgrade commands.
Requires read/write permission for the HID transport, not for device flash.
"""
import argparse
import json
import os
import select
import time
from pathlib import Path
from read_hd350_usb_features import EXPECTED

REQUESTS = {
    'connect': bytes.fromhex('17000000'),
    'version': bytes.fromhex('01000000'),
    'mode': bytes.fromhex('09000000'),
    'product': bytes.fromhex('1d000000'),
    'build': bytes.fromhex('1f000000'),
    'prompt_readonly': bytes.fromhex('050000020264'),  # 612
    'prompt_settings': bytes.fromhex('05000002026b'),  # 619
    'disconnect': bytes.fromhex('19000000'),
}


def query(fd, name, log):
    payload = REQUESTS[name]
    request = bytes([1, len(payload)]) + payload
    request = request.ljust(66, b'\0')
    entry = {'name': name, 'requestHex': request.hex(), 'responses': []}
    log.append(entry)
    if os.write(fd, request) != len(request):
        raise RuntimeError('short HID write; no retry')
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if not select.select([fd], [], [], max(0, deadline - time.monotonic()))[0]:
            break
        data = os.read(fd, 256)
        entry['responses'].append(data.hex())
        if len(data) < 8 or data[0] != 2 or data[2] != payload[0] + 1:
            continue
        length = int.from_bytes(data[4:6], 'big')
        if not 2 <= length <= 60 or len(data) < 6 + length or data[1] != length + 4:
            raise RuntimeError('incomplete or inconsistent AHI response')
        if data[3] != 0:
            raise RuntimeError('unexpected multipart reply for bounded query')
        body = data[6:6 + length]
        if payload[0] == 5:
            if len(body) < 6 or body[:2] != payload[4:6]:
                raise RuntimeError('configuration response identity mismatch')
            entry['status'] = int.from_bytes(body[2:4], 'big')
            entry['configBytes'] = int.from_bytes(body[4:6], 'big')
            entry['payloadHex'] = body[6:].hex()
            if entry['configBytes'] != len(body[6:]):
                raise RuntimeError('configuration response size mismatch')
        else:
            entry['status'] = int.from_bytes(body[:2], 'big')
            entry['payloadHex'] = body[2:].hex()
        return entry
    raise TimeoutError('no matching AHI response; no retry')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('device', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError('capture exists')
    if args.device.parent != Path('/dev') or not args.device.name.startswith('hidraw'):
        raise ValueError('expected /dev/hidrawN')
    p = Path('/sys/class/hidraw') / args.device.name / 'device'
    u = dict(line.split('=', 1) for line in (p / 'uevent').read_text().splitlines())
    if (u.get('HID_ID') != '0003:00001377:00006012'
            or not u.get('HID_PHYS', '').endswith('/input2')
            or (p / 'report_descriptor').read_bytes() != EXPECTED):
        raise ValueError('USB identity/descriptor mismatch')
    log = []
    fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
    connected = False
    try:
        connected = query(fd, 'connect', log).get('status') == 0
        if not connected:
            raise RuntimeError('AHI connection rejected')
        for name in ('version', 'mode', 'product', 'build', 'prompt_readonly', 'prompt_settings'):
            query(fd, name, log)
    finally:
        try:
            if connected and query(fd, 'disconnect', log).get('status') != 0:
                raise RuntimeError('AHI disconnect not confirmed')
        finally:
            os.close(fd)
            with args.output.open('x') as f:
                json.dump(log, f, indent=2)
                f.write('\n')
            print(json.dumps([{k: v for k, v in e.items() if k not in
                               ('requestHex', 'responses')} for e in log], indent=2))


if __name__ == '__main__':
    main()
