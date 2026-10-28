#!/usr/bin/env python3
"""Experimental narrow Kalimba compact-call decoder, checked against linked symbols.

Not a general disassembler. Scanning aligned halfwords can find false positives;
outputs are candidate calls until instruction boundaries are established.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def long_call(data, offset, address):
    prefix, word = struct.unpack_from('<HH', data, offset)
    if prefix >> 12 != 15 or word & 0xf0e1 != 0xe021:
        return None
    displacement = ((prefix & 0xfff) << 8) | ((word >> 4) & 0xf0) | ((word >> 1) & 15)
    if displacement & 0x80000:
        displacement -= 1 << 20
    return address + 2 * displacement


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('calibration', type=Path)
    parser.add_argument('firmware', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('output exists')
    checked = []
    for entry in json.loads(args.calibration.read_text()):
        target = long_call(bytes.fromhex(entry['hex']), 0, entry['address'])
        if target is None:
            continue
        if target != entry['destination']:
            raise ValueError('linked-symbol calibration mismatch: '+entry['label'])
        checked.append(entry['label'])
    if len(checked) < 13:
        raise ValueError('insufficient calibration examples')
    data = args.firmware.read_bytes()
    # This candidate range was localized in the exact stock 5.5.0 image.
    digest = hashlib.sha256(data).hexdigest()
    if digest != '25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48':
        raise ValueError('not pinned stock 5.5.0 firmware')
    calls = []
    for offset in range(0x12332a, 0x12335a, 2):
        target = long_call(data, offset, offset)
        if target is not None:
            calls.append({'fileOffset': hex(offset), 'targetFileOffset': hex(target),
                          'instructionHex': data[offset:offset+4].hex()})
    result = {'firmwareSha256': digest, 'validatedReferenceLabels': checked,
              'candidateRange': ['0x12332a', '0x12335a'], 'candidateCalls': calls}
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
