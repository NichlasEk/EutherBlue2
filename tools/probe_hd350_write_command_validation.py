#!/usr/bin/env python3
"""Recognize write handlers using inputs rejected BEFORE writing in pinned5.5.0.

STORE_PS_KEY has ZERO payload bytes (not a key with zero data, which deletes).
Stock store handler at1528e0 matches reference exactly outside long calls;
length<2 returns INVALID_PARAMETER before allocation or PsStore.
OPEN_FILE mode02 is rejected by its read-only handler before FileFind.
OPEN_STORAGE_PARTITION has zero payload; reference requires3/7 before open.
No valid write request, partition identifier, key identifier, or firmware data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
from read_hd350_gaia_file import Gaia

QUERIES = (
    ('storePsEmptyPayload', 0x0712, b''),
    ('openFileOverwriteRejected', 0x0621, b'\x02prompts/10.prm'),
    ('openStorageEmptyPayload', 0x0611, b''),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    stock = Path('artifacts/extracted/hd350bt/firmware-5.5.0/HD350_firmware_v5.5.0.bin')
    if hashlib.sha256(stock.read_bytes()).hexdigest() != '25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48':
        raise ValueError('Stock hash mismatch')
    result = {'transactions': [], 'replies': {}}
    with args.output.open('x') as capture:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(5)
        try:
            sock.connect(('00:00:00:00:00:00', 1))
            gaia = Gaia(sock, result['transactions'])
            if gaia.query(0x0494, 0x0280) != bytes.fromhex('00000500050000'):
                raise ValueError('Expected firmware5.5.0 not confirmed')
            for name, command, payload in QUERIES:
                reply = gaia.query(0x000a, command, payload)
                result['replies'][name] = reply.hex()
                if reply[0] not in (1, 2, 3, 5, 6):
                    raise ValueError('Unexpected status; stop without further commands')
            result['postVersionReply'] = gaia.query(0x0494, 0x0280).hex()
        except Exception as error:
            result['error'] = str(error)
        finally:
            sock.close()
            json.dump(result, capture, indent=2); capture.write('\n')
            print(json.dumps({k:v for k,v in result.items() if k != 'transactions'}, indent=2))


if __name__ == '__main__':
    main()
