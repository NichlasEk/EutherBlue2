#!/usr/bin/env python3
"""One HD350 product-version GET over the SDP-confirmed GAIA RFCOMM channel."""
from local_device import bluetooth_address
import argparse
import json
from pathlib import Path
import socket
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('capture exists')
    address = bluetooth_address()
    request = bytes.fromhex('ff01000004940280')
    result = {'address': address, 'channel': 1, 'requestHex': request.hex(), 'received': []}
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.settimeout(5)
    try:
        sock.connect((address, 1))
        sock.sendall(request)
        deadline = time.monotonic() + 5
        buffer = bytearray()
        while time.monotonic() < deadline:
            sock.settimeout(max(0.01, deadline-time.monotonic()))
            chunk = sock.recv(1024)
            if not chunk:
                raise RuntimeError('connection closed before reply')
            result['received'].append(chunk.hex())
            buffer.extend(chunk)
            if len(buffer) > 8192:
                raise ValueError('response limit exceeded')
            while len(buffer) >= 8:
                if buffer[0] != 255 or buffer[1] != 1 or buffer[2] & ~1:
                    raise ValueError('unexpected GAIA framing')
                size = 8 + buffer[3] + (buffer[2] & 1)
                if len(buffer) < size:
                    break
                frame = bytes(buffer[:size]); del buffer[:size]
                if frame[2] & 1:
                    checksum = 0
                    for value in frame:
                        checksum ^= value
                    if checksum:
                        raise ValueError('bad checksum')
                if frame[4:8] != bytes.fromhex('04948280'):
                    continue
                payload = frame[8:8+frame[3]]
                if not payload:
                    raise ValueError('missing status')
                result['status'] = payload[0]
                result['payloadHex'] = payload.hex()
                if payload[0] == 0 and len(payload) == 7:
                    result['versionFields'] = [int.from_bytes(payload[i:i+2], 'big') for i in (1,3,5)]
                    result['version'] = '.'.join(map(str,result['versionFields']))
                return
        raise TimeoutError('no matching reply')
    except Exception as error:
        result['error'] = str(error)
    finally:
        sock.close()
        with args.output.open('x') as out:
            json.dump(result, out, indent=2); out.write('\n')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
