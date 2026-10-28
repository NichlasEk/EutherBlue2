#!/usr/bin/env python3
"""Verify HD350 OTA offline using a key extracted from pinned official stock.

Requires Python cryptography. No network, Bluetooth, signing or firmware writes.
The stock hash pins the trust source; a candidate cannot supply its own key.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, utils

STOCK_SHA256 = 'cf4a07ddefc6b7c3225a42c21592f9ccae5fed08b88b7f15b95372526ee99df6'
PARTITIONS = (0, 1, 4, 5, 6, 7, 9)
KEY_OFFSET = 0x6f664  # relative to section 9 data, after PARTDATA identifiers


def parse(data):
    offset = 0
    blocks = []
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError('truncated header')
        tag, size = struct.unpack_from('>8sI', data, offset)
        end = offset + 12 + size
        if end > len(data):
            raise ValueError('truncated payload')
        blocks.append((tag, data[offset + 12:end], offset + 12))
        offset = end
    if len(blocks) != 9 or blocks[0][0] != b'APPUHDR5' or blocks[-1][0] != b'APPUPFTR':
        raise ValueError('unexpected block layout')
    header = blocks[0][1]
    if len(header) != 36 or header[:8] != b'QCC512Xx' or header[-2:] != b'\0\1':
        raise ValueError('unexpected variant/header/signing mode')
    parts = {}
    positions = {}
    for tag, body, pos in blocks[1:-1]:
        if tag != b'PARTDATA' or len(body) < 4:
            raise ValueError('unexpected partition')
        kind, number = struct.unpack_from('>HH', body)
        if kind != 0 or number in parts:
            raise ValueError('unexpected partition type or duplicate')
        parts[number] = body[4:]
        positions[number] = pos + 4
    if tuple(parts) != PARTITIONS or len(blocks[-1][1]) != 256:
        raise ValueError('unexpected partition sequence or signature length')
    return parts, positions, blocks[-1][1]


def load_key(stock):
    if hashlib.sha256(stock).hexdigest() != STOCK_SHA256:
        raise ValueError('trust source is not pinned official 5.8.0 stock')
    parts, _, _ = parse(stock)
    words = parts[9][KEY_OFFSET:KEY_OFFSET + 256]
    modulus = b''.join(words[i:i + 2][::-1] for i in range(0, 256, 2))
    return rsa.RSAPublicNumbers(65537, int.from_bytes(modulus, 'big')).public_key()


def verify(data, key):
    parts, _, signature = parse(data)
    digest = hashlib.sha256(b''.join(parts[n] for n in PARTITIONS)).digest()
    try:
        key.verify(signature, digest,
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=222),
                   utils.Prehashed(hashes.SHA256()))
        valid = True
    except InvalidSignature:
        valid = False
    return {'sha256': hashlib.sha256(data).hexdigest(), 'signatureValid': valid,
            'signedSections': list(PARTITIONS), 'signedContentSha256': digest.hex(),
            'algorithm': 'RSA-2048/PSS/SHA-256', 'saltBytes': 222,
            'deviceEnforcementTested': False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stock', required=True, type=Path)
    ap.add_argument('--negative-check', action='store_true',
                    help='flip one byte of prompts/10.prm in memory; write no firmware')
    ap.add_argument('firmware', nargs='+', type=Path)
    args = ap.parse_args()
    stock = args.stock.read_bytes()
    key = load_key(stock)
    if not verify(stock, key)['signatureValid']:
        raise ValueError('pinned original does not verify')
    results = []
    failed = False
    for path in args.firmware:
        result = verify(path.read_bytes(), key)
        result['file'] = str(path)
        failed |= not result['signatureValid']
        results.append(result)
    if args.negative_check:
        parts, positions, _ = parse(stock)
        fs = parts[7]
        _, size, count = struct.unpack_from('<4sII', fs)
        target = None
        for i in range(count):
            name, offset, length = struct.unpack_from('<III', fs, 12 + i * 12)
            if name & 0x80000000:
                continue
            n = struct.unpack_from('<H', fs, name)[0]
            if fs[name + 2:name + 2 + n] == b'10.prm':
                if not length or offset + length > size:
                    raise ValueError('bad prompt extent')
                target = positions[7] + offset
        if target is None:
            raise ValueError('prompt 10 not found')
        mutated = bytearray(stock)
        mutated[target] ^= 1
        rejected = not verify(bytes(mutated), key)['signatureValid']
        results.append({'check': 'one byte changed in prompt 10', 'rejected': rejected,
                        'firmwareWritten': False})
        failed |= not rejected
    print(json.dumps(results, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
