#!/usr/bin/env python3
"""HD350 HID upgrade transport identity only; no SYNC/START/DATA/ABORT."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import select
import time
from read_hd350_usb_features import EXPECTED


def receive(fd, log):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if not select.select([fd], [], [], max(0, deadline-time.monotonic()))[0]:
            break
        data = os.read(fd, 256)
        log.append({'received': data.hex()})
        if len(data) < 2 or data[0] != 6:
            continue
        if not 0 < data[1] <= 12 or len(data) < data[1] + 2:
            raise ValueError('invalid response length')
        return data[2:2+data[1]]
    raise TimeoutError('no report 6 response; no retry')


def command(fd, value, log):
    if value not in (2, 7):
        raise ValueError('only connect/disconnect allowed')
    data = bytearray([3, 2, value, 0])
    log.append({'command': 'connect' if value == 2 else 'disconnect', 'sent': data.hex()})
    fcntl.ioctl(fd, 0xC0044806, data, True)  # HIDIOCSFEATURE, descriptor size 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('capture exists')
    if args.device.parent != Path('/dev') or not args.device.name.startswith('hidraw'):
        raise ValueError('expected /dev/hidrawN')
    p = Path('/sys/class/hidraw') / args.device.name / 'device'
    u = dict(line.split('=', 1) for line in (p/'uevent').read_text().splitlines())
    if (u.get('HID_ID') != '0003:00001377:00006012'
            or not u.get('HID_PHYS', '').endswith('/input2')
            or (p/'report_descriptor').read_bytes() != EXPECTED):
        raise ValueError('identity/descriptor mismatch')
    log = []
    result = {'device': str(args.device), 'log': log}
    fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
    connected = False
    try:
        command(fd, 2, log)
        status = receive(fd, log)
        if status not in (b'\0', b'\0\0'):
            raise RuntimeError('transport rejected connection: '+status.hex())
        connected = True
        for opcode, name in ((0x19, 'version'), (0x1b, 'variant')):
            data = bytes([5, 3, opcode, 0, 0]).ljust(66, b'\0')
            log.append({'query': name, 'sent': data.hex()})
            if os.write(fd, data) != len(data):
                raise RuntimeError('short write; no retry')
            reply = receive(fd, log)
            if (len(reply) < 3 or reply[0] != opcode + 1
                    or int.from_bytes(reply[1:3], 'big') != len(reply)-3):
                raise ValueError('unexpected identity reply: '+reply.hex())
            body = reply[3:]
            result[name+'Hex'] = body.hex()
            if name == 'version' and len(body) == 6:
                result['versionFields'] = [int.from_bytes(body[i:i+2], 'big') for i in (0,2,4)]
            if name == 'variant':
                result['variantText'] = body.decode('ascii', errors='backslashreplace').rstrip('\0')
    except Exception as error:
        result['error'] = str(error)
    finally:
        try:
            if connected:
                command(fd, 7, log)
                result['disconnectSent'] = True
                # Reference transport does not forward a disconnect confirmation.
        finally:
            os.close(fd)
            with args.output.open('x') as out:
                json.dump(result, out, indent=2)
                out.write('\n')
            print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
