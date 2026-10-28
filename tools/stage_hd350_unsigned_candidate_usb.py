#!/usr/bin/env python3
"""Stage a guarded HD 350BT prompt-only candidate, stopping before APPUPFTR.

This writes only through the headset's upgrade transport.  It never sends the
footer, TRANSFER_COMPLETE_RES, COMMIT, ABORT, ERASE, reset, or a bank-swap
request.  The active bank is not selected by this tool.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import time

from read_hd350_usb_features import EXPECTED
from probe_hd350_hidden_usb_audio import check_stock


FOOTER_OFFSET = 0x17A798
MAX_VM_PACKET = 64
MAX_DATA_CHUNK = MAX_VM_PACKET - 4


def packet(opcode, data=b''):
    value = bytes((opcode,)) + len(data).to_bytes(2, 'big') + data
    if len(value) > MAX_VM_PACKET:
        raise ValueError('VM packet exceeds USB transport')
    return value


def identify(device):
    if device.parent != Path('/dev') or not device.name.startswith('hidraw'):
        raise ValueError('expected /dev/hidrawN')
    node = Path('/sys/class/hidraw') / device.name / 'device'
    uevent = dict(line.split('=', 1) for line in (node / 'uevent').read_text().splitlines())
    if (uevent.get('HID_ID') != '0003:00001377:00006012'
            or not uevent.get('HID_PHYS', '').endswith('/input2')
            or (node / 'report_descriptor').read_bytes() != EXPECTED):
        raise ValueError('HD 350BT upgrade interface identity/descriptor mismatch')


def transport_command(fd, value, journal):
    if value not in (2, 7):
        raise ValueError('only USB transport connect/disconnect is permitted')
    report = bytearray((3, 2, value, 0))
    journal.append({'direction': 'out', 'kind': 'connect' if value == 2 else 'disconnect',
                    'report': report.hex()})
    fcntl.ioctl(fd, 0xC0044806, report, True)


def send_vm(fd, value, journal, log=True):
    report = bytes((5, len(value))) + value
    report = report.ljust(66, b'\0')
    if log:
        journal.append({'direction': 'out', 'kind': 'vm', 'packet': value.hex()})
    if os.write(fd, report) != len(report):
        raise RuntimeError('short USB HID write; no retry')


def receive(fd, journal, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = select.select([fd], [], [], max(0, deadline - time.monotonic()))[0]
        if not ready:
            break
        report = os.read(fd, 256)
        journal.append({'direction': 'in', 'report': report.hex()})
        if len(report) < 2 or report[0] != 6:
            continue
        length = report[1]
        if not 0 < length <= 12 or len(report) < length + 2:
            raise ValueError('invalid USB response report length')
        return report[2:2 + length]
    raise TimeoutError('no USB upgrade response; no retry')


def expect(packet_value, opcode, length=None):
    if len(packet_value) < 3 or packet_value[0] != opcode:
        raise ValueError(f'expected opcode 0x{opcode:02x}, got {packet_value.hex()}')
    declared = int.from_bytes(packet_value[1:3], 'big')
    if declared != len(packet_value) - 3 or (length is not None and len(packet_value) != length):
        raise ValueError('malformed VM response: ' + packet_value.hex())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    check_stock()
    identify(args.device)
    image = args.candidate.read_bytes()
    manifest = json.loads(args.manifest.read_text())
    expected_sha = hashlib.sha256(image).hexdigest()
    session_id = bytes.fromhex(expected_sha[:8])
    prompt_only = (
        manifest.get('allOtherBytesIdentical') is True
        or (
            manifest.get('filesystemMetadataChanged') is False
            and manifest.get('speechTempoChanged') is False
            and manifest.get('speechTruncated') is False
            and set(manifest.get('onlyChangedFiles', []))
            == {f'prompts/{number}.prm' for number in range(13)}
        )
    )
    if (manifest.get('sha256') != expected_sha
            or manifest.get('size') != len(image)
            or manifest['signatureValid'] is not False
            or not prompt_only
            or image[FOOTER_OFFSET:FOOTER_OFFSET + 8] != b'APPUPFTR'):
        raise ValueError('candidate or footer boundary mismatch')

    guard = {'offlineGuards': 'passed', 'device': str(args.device),
             'candidate': str(args.candidate), 'manifest': str(args.manifest),
             'candidateSha256': expected_sha, 'sessionId': session_id.hex(),
             'bytesBeforeFooter': FOOTER_OFFSET,
             'maxDataChunk': MAX_DATA_CHUNK,
             'forbiddenOpcodes': [0x07, 0x0c, 0x0f],
             'bankSwapRequested': False, 'footerSent': False}
    if not args.execute:
        print(json.dumps(guard, indent=2))
        return
    if args.output is None:
        parser.error('--output is required with --execute')
    if args.output.exists():
        raise ValueError('capture already exists')

    result = dict(guard)
    result.update({'journal': [], 'bytesSent': 0, 'dataPacketsSent': 0, 'requests': 0,
                   'fileCursor': 0,
                   'mutationAttempted': False})
    with args.output.open('x+') as capture:
        def save():
            capture.seek(0)
            json.dump(result, capture, indent=2)
            capture.write('\n')
            capture.truncate()
            capture.flush()
            os.fsync(capture.fileno())

        fd = None
        connected = False
        try:
            fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
            transport_command(fd, 2, result['journal'])
            status = receive(fd, result['journal'])
            result['connectStatus'] = status.hex()
            save()
            if status not in (b'\0', b'\0\0'):
                raise RuntimeError('USB transport rejected connection: ' + status.hex())
            connected = True

            send_vm(fd, packet(0x19), result['journal'])
            version = receive(fd, result['journal'])
            expect(version, 0x1a)
            result['upgradeVersion'] = version.hex()
            if version[3:] != bytes.fromhex('000100000001'):
                raise ValueError('unexpected USB upgrade protocol version')

            send_vm(fd, packet(0x13, session_id), result['journal'])
            sync = receive(fd, result['journal'])
            expect(sync, 0x14, 9)
            result['sync'] = sync.hex()
            save()
            if sync[3] != 0 or sync[4:8] != session_id:
                raise ValueError('fresh resume point 0/session id not confirmed')

            send_vm(fd, packet(0x01), result['journal'])
            started = receive(fd, result['journal'])
            expect(started, 0x02, 6)
            result['start'] = started.hex()
            save()
            if started[3] != 0:
                raise ValueError('START rejected: ' + started.hex())

            result['mutationAttempted'] = True
            save()
            send_vm(fd, packet(0x15), result['journal'])
            next_progress = 65536
            result['requestSamples'] = []
            while True:
                request_journal = []
                request = receive(fd, request_journal, timeout=120)
                expect(request, 0x03, 11)
                size = int.from_bytes(request[3:7], 'big')
                transport_offset = int.from_bytes(request[7:11], 'big')
                cursor = result['fileCursor']
                if not size or cursor > FOOTER_OFFSET or cursor + size > len(image):
                    raise ValueError(f'invalid data request fileCursor={cursor} size={size}')
                # The VM offset is relative to the parser's current object
                # (header or partition), not an absolute offset in the DFU.
                # A fresh transfer must start each newly requested object at 0.
                if transport_offset != 0:
                    raise ValueError(f'nonzero resume offset {transport_offset} in fresh transfer')
                result['requests'] += 1
                result['lastRequest'] = {'fileOffset': cursor,
                                         'transportOffset': transport_offset,
                                         'size': size}
                if result['requests'] <= 8:
                    result['requestSamples'].extend(request_journal)
                if cursor == FOOTER_OFFSET:
                    result['stoppedAtFooterRequest'] = True
                    break
                if cursor + size > FOOTER_OFFSET:
                    raise ValueError('request crosses footer boundary; no bytes sent for it')
                block = image[cursor:cursor + size]
                for position in range(0, len(block), MAX_DATA_CHUNK):
                    chunk = block[position:position + MAX_DATA_CHUNK]
                    # moreData=0: the complete upgrade file has additional bytes.
                    send_vm(fd, packet(0x04, b'\0' + chunk), result['journal'], log=False)
                    result['bytesSent'] += len(chunk)
                    result['dataPacketsSent'] += 1
                result['fileCursor'] += size
                if result['bytesSent'] >= next_progress:
                    result['requestSamples'].extend(request_journal)
                    print(json.dumps({'stagedBytes': result['bytesSent'],
                                      'percent': round(100 * result['bytesSent'] / FOOTER_OFFSET, 1)}),
                          flush=True)
                    next_progress = result['bytesSent'] + 65536
                    save()

            transport_command(fd, 7, result['journal'])
            connected = False
            result['completed'] = 'All pre-footer bytes accepted; footer and apply commands withheld'
        except Exception as error:
            result['error'] = str(error)
            if fd is not None and connected:
                try:
                    transport_command(fd, 7, result['journal'])
                    result['errorDisconnectSent'] = True
                except Exception as disconnect_error:
                    result['disconnectError'] = str(disconnect_error)
        finally:
            if fd is not None:
                os.close(fd)
            save()

    print(json.dumps({key: value for key, value in result.items() if key != 'journal'}, indent=2))


if __name__ == '__main__':
    main()
