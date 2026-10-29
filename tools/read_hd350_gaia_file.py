#!/usr/bin/env python3
"""Bounded GAIA read of stock prompts/10.prm; no partition or upgrade writes.

OPEN_FILE 0621 mode00, READ_FILE0624, CLOSE_FILE0628 follow ADK gaia.c.
An open read stream is volatile state; always attempt close after success.
"""
from local_device import bluetooth_address
import argparse
import hashlib
import json
from pathlib import Path
import socket
import time


class Gaia:
    def __init__(self, sock, log):
        self.sock, self.log, self.buffer = sock, log, bytearray()

    def query(self, vendor, command, payload=b''):
        request = bytes([255, 1, 0, len(payload)]) + vendor.to_bytes(2, 'big') + command.to_bytes(2, 'big') + payload
        entry = {'requestHex': request.hex(), 'frames': []}
        self.log.append(entry)
        self.sock.sendall(request)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            while len(self.buffer) >= 8:
                if self.buffer[:2] != b'\xff\x01' or self.buffer[2] & ~1:
                    raise ValueError('Unexpected GAIA framing')
                size = 8 + self.buffer[3] + (self.buffer[2] & 1)
                if len(self.buffer) < size:
                    break
                frame = bytes(self.buffer[:size]); del self.buffer[:size]
                entry['frames'].append(frame.hex())
                if frame[2] & 1:
                    check = 0
                    for byte in frame:
                        check ^= byte
                    if check:
                        raise ValueError('Checksum mismatch')
                if frame[4:8] == vendor.to_bytes(2, 'big') + (command | 0x8000).to_bytes(2, 'big'):
                    reply = frame[8:8+frame[3]]
                    if not reply:
                        raise ValueError('Missing status')
                    entry['status'] = reply[0]
                    return reply
                if len(entry['frames']) > 32:
                    raise ValueError('Unrelated frame limit')
            self.sock.settimeout(max(.01, deadline-time.monotonic()))
            chunk = self.sock.recv(1024)
            if not chunk:
                raise EOFError('GAIA connection closed')
            self.buffer.extend(chunk)
            if len(self.buffer) > 8192:
                raise ValueError('Buffer limit')
        raise TimeoutError('GAIA response timeout')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--channel', type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.channel <= 30:
        raise ValueError('RFCOMM channel must be 1..30')
    result = {'address': bluetooth_address(), 'file': 'prompts/10.prm', 'transactions': []}
    result['rfcommChannel'] = args.channel
    # Reserve capture before any device operation.
    with args.output.open('x') as capture:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        stream = None
        gaia = Gaia(sock, result['transactions'])
        data = bytearray()
        try:
            sock.settimeout(5)
            sock.connect((result['address'], args.channel))
            version = gaia.query(0x0494, 0x0280)
            if version != bytes.fromhex('00000500050000'):
                raise ValueError('Expected firmware5.5.0 not confirmed')
            opened = gaia.query(0x000a, 0x0621, b'\0prompts/10.prm')
            if opened[0] != 0:
                result['openStatus'] = opened[0]
                return
            if len(opened) != 2:
                raise ValueError('Invalid open reply')
            stream = opened[1]
            deadline = time.monotonic() + 60
            for sequence in range(256):
                if time.monotonic() >= deadline:
                    raise TimeoutError('Read deadline')
                header = bytes([stream]) + sequence.to_bytes(4, 'big')
                reply = gaia.query(0x000a, 0x0624, header)
                if reply[0] or len(reply) < 6 or reply[1:6] != header:
                    raise ValueError('Invalid read response')
                if len(reply) == 6:
                    result['eof'] = True
                    break
                data.extend(reply[6:])
                if len(data) > 32768:
                    raise ValueError('File size limit')
            else:
                raise ValueError('Packet limit')
            result['bytes'] = len(data)
            result['sha256'] = hashlib.sha256(data).hexdigest()
            stock = Path('artifacts/extracted/hd350bt/inspection-5.5.0/000995d4-PARTDATA/prompts/10.prm')
            result['matchesStock'] = data == stock.read_bytes()
        except Exception as error:
            result['error'] = str(error)
        finally:
            if stream is not None:
                try:
                    result['closeReply'] = gaia.query(0x000a, 0x0628, bytes([stream])).hex()
                except Exception as error:
                    result['closeError'] = str(error)
            sock.close()
            json.dump(result, capture, indent=2); capture.write('\n')
            print(json.dumps({k:v for k,v in result.items() if k != 'transactions'}, indent=2))


if __name__ == '__main__':
    main()
