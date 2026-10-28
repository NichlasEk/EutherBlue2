#!/usr/bin/env python3
"""Offline byte anchors for named HID functions in a linked Kalimba reference.

Requires pyelftools. Results are candidates, not decoded instructions.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile

NAMES = {'_usbHostHandleMessage', '_hidConsumerHandler', '_hidKeyboardHandler',
         '_hidDatalinkHandler', '_handleHidClassRequest',
         '_usbEnumerateHidConsumerTransportControl'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('firmware', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--name', action='append', dest='names',
                        help='exact linked symbol to match; repeatable')
    args = parser.parse_args()
    names = set(args.names or NAMES)
    if args.output.exists():
        raise ValueError('output exists')
    firmware = args.firmware.read_bytes()
    results = []
    with args.reference.open('rb') as source:
        elf = ELFFile(source)
        symbols = list(elf.get_section_by_name('.symtab').iter_symbols())
        # Lc_* labels can also have FUNC type; exclude these internal labels.
        starts = sorted({s['st_value'] for s in symbols
                         if s['st_info']['type'] == 'STT_FUNC'
                         and s.name.startswith(('_', '$_'))})
        for symbol in symbols:
            if symbol.name not in names:
                continue
            section = elf.get_section(symbol['st_shndx'])
            address = symbol['st_value']
            end = next(x for x in starts if x > address)
            start = address - section['sh_addr']
            code = section.data()[start:start + end-address]
            votes = Counter()
            for offset in range(0, len(code)-7, 2):
                position = 0
                while (position := firmware.find(code[offset:offset+8], position)) >= 0:
                    votes[position-offset] += 1
                    position += 1
            candidates = []
            for base, count in votes.most_common(4):
                if base < 0 or base+len(code) > len(firmware):
                    continue
                target = firmware[base:base+len(code)]
                candidates.append({'fileOffset': hex(base), 'overlapping8ByteAnchors': count,
                                   'equalBytesAtSameOffset': sum(a == b for a,b in zip(code,target))})
            results.append({'name': symbol.name, 'referenceAddress': hex(address),
                            'referenceBytes': len(code), 'candidates': candidates})
    args.output.write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
