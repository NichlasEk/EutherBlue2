#!/usr/bin/env python3
"""Offline calibration of one compact compare form and USB branch-table inventory.

Does not decode arbitrary prefixed instructions or emit device commands.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def compare(word):
    if word & 0xf407 != 0x2400:
        return None
    return ((word >> 3) & 7, ((word >> 6) & 15) | ((word >> 7) & 16))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('calibration', type=Path)
    ap.add_argument('firmware', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError('output exists')
    checked = []
    for row in json.loads(args.calibration.read_text()):
        # Larger immediates can be lowered to different sequences by the linker;
        # they do not calibrate this unprefixed short-compare form.
        if row['immediate'] > 31 or row['register'] > 7:
            continue
        word = int.from_bytes(bytes.fromhex(row['linked'])[:2], 'little')
        decoded = compare(word)
        if decoded is None:
            continue
        if decoded != (row['register'], row['immediate']):
            raise ValueError('compare calibration mismatch: '+row['name'])
        checked.append(row['name'])
    if len(checked) < 47:
        raise ValueError('insufficient calibration')
    data = args.firmware.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != '25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48':
        raise ValueError('not pinned original 5.5.0')
    tests = []
    for offset in (0x123338, 0x123342):
        word = struct.unpack_from('<H', data, offset)[0]
        decoded = compare(word)
        if decoded is None:
            raise ValueError('unexpected dispatch bytes')
        tests.append({'fileOffset': hex(offset), 'word': hex(word),
                      'register': decoded[0], 'immediate': decoded[1]})
    tables = []
    for start, count in ((0x170ab8,10), (0x170ae0,8), (0x170b00,9)):
        entries = []
        for i in range(count):
            value = struct.unpack_from('<I',data,start+4*i)[0]
            target = 0x106a5c + (value & 0x7ffffffe)
            if not 0x12354c <= target < 0x12385a:
                raise ValueError('table target outside candidate function')
            entries.append({'index':i,'rawPointer':hex(value),'targetFileOffset':hex(target)})
        tables.append({'fileOffset':hex(start),'entries':entries})
    result = {'firmwareSha256':digest,'validatedCompareLabels':checked,
              'dispatchComparisons':tests,'candidateTables':tables,
              'note':'Table indices are not established command IDs; no packet format inferred.'}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'validatedComparisons':len(checked),'dispatchComparisons':tests,
                      'candidateTableLengths':[len(t['entries']) for t in tables]},indent=2))


if __name__ == '__main__':
    main()
