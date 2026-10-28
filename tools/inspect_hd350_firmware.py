#!/usr/bin/env python3
"""Offline extraction of HD350 APPUHDR5 blocks and byte-addressed File images.

No device I/O, firmware writing, signature repair or repacking. Input is the
decrypted DFU .bin. All output is local and the input is preserved.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def filesystem(data, output):
    magic, size, count = struct.unpack_from('<4sII', data)
    require(magic == b'File' and size == len(data), 'File image size mismatch')
    require(0 < count <= (size - 12) // 12, 'invalid entry count')
    entries = [struct.unpack_from('<III', data, 12 + i * 12) for i in range(count)]
    seen = set()
    files = []

    def visit(index, parent, root=False):
        require(0 <= index < count and index not in seen, 'invalid/cyclic entry')
        seen.add(index)
        flags, offset, length = entries[index]
        name_offset = flags & 0x7fffffff
        if root:
            require(flags == 0x80000000, 'unexpected root entry')
            path = parent
        else:
            require(12 + count * 12 <= name_offset <= size - 2, 'invalid name offset')
            name_length = struct.unpack_from('<H', data, name_offset)[0]
            end = name_offset + 2 + name_length
            require(end <= size, 'name extends outside image')
            name = data[name_offset + 2:end].decode('ascii')
            require(name not in ('', '.', '..') and '/' not in name and '\\' not in name,
                    'unsafe filename')
            path = parent / name
        if flags & 0x80000000:
            require(1 <= offset <= count and offset - 1 + length <= count, 'invalid children')
            for child in range(offset - 1, offset - 1 + length):
                visit(child, path)
        else:
            require(offset >= 12 + count * 12 and offset + length <= size, 'invalid file extent')
            payload = data[offset:offset + length]
            path.parent.mkdir(parents=True, exist_ok=True)
            require(not path.exists(), 'refusing existing output file')
            path.write_bytes(payload)
            files.append({'path': str(path.relative_to(output)), 'offset': offset,
                          'size': length, 'sha256': hashlib.sha256(payload).hexdigest()})

    visit(0, output, root=True)
    require(len(seen) == count, 'unreachable filesystem entries')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('firmware', type=Path)
    parser.add_argument('output', type=Path, help='new output directory')
    args = parser.parse_args()
    data = args.firmware.read_bytes()
    require(data.startswith(b'APPUHDR5'), 'not APPUHDR5 firmware')
    require(not args.output.exists(), 'output directory must not exist')
    blocks = []
    offset = 0
    while offset < len(data):
        require(offset + 12 <= len(data), 'truncated block header')
        tag, size = struct.unpack_from('>8sI', data, offset)
        require(tag in (b'APPUHDR5', b'PARTDATA', b'APPUPFTR'), 'unknown block tag')
        end = offset + 12 + size
        require(end <= len(data), 'truncated block payload')
        blocks.append((offset, tag, data[offset + 12:end]))
        offset = end
    require(blocks[-1][1] == b'APPUPFTR', 'missing footer')
    require(b''.join(tag + struct.pack('>I', len(body)) + body for _, tag, body in blocks)
            == data, 'block roundtrip differs')
    args.output.mkdir(parents=True)
    report = {'inputSha256': hashlib.sha256(data).hexdigest(), 'size': len(data),
              'blockRoundtripIdentical': True, 'signatureVerified': False, 'blocks': []}
    for offset, tag, body in blocks:
        item = {'offset': offset, 'tag': tag.decode(), 'size': len(body)}
        name = f'{offset:08x}-{tag.decode()}'
        (args.output / (name + '.bin')).write_bytes(body)
        if tag == b'PARTDATA':
            require(len(body) >= 4, 'missing partition identifier')
            item['partition'] = int.from_bytes(body[:4], 'big')
            if body[4:8] == b'File':
                item['files'] = filesystem(body[4:], args.output / name)
        report['blocks'].append(item)
    (args.output / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'size': len(data), 'blocks': len(blocks),
                      'files': sum(len(b.get('files', [])) for b in report['blocks']),
                      'blockRoundtripIdentical': True, 'signatureVerified': False}))


if __name__ == '__main__':
    main()
