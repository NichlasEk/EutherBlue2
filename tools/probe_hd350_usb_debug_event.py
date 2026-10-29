#!/usr/bin/env python3
"""One documented Enable USB Debug event, with pre/post identity and USB inventory.

Evidence: stock5.5 config_definition.gz enum109, sink_events.h EventUsrEnableUsbDebug
4109, sink main.c ENABLE_ALLOW_USB_DEBUG handler, UsbDebugAllow(TRUE) wrapper.
Handler inclusion on stock is NOT established. Reference changes cached permission
only, still requires challenge-response, and loses permission on curator reset.
No upgrade data, PS store, reset, unlock-key write, or opcode sweep.
"""
from local_device import bluetooth_address
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import socket
import time
import xml.etree.ElementTree as ET
from read_hd350_gaia_file import Gaia

EVENT = bytes.fromhex('ff010002000a07214109')
STOCK = Path('artifacts/extracted/hd350bt/firmware-5.5.0/HD350_firmware_v5.5.0.bin')
CONFIG = Path('artifacts/extracted/hd350bt/inspection-5.5.0/000995d4-PARTDATA/config_definition.gz')


def usb_inventory():
    rows = []
    for p in sorted(Path('/sys/bus/usb/devices').iterdir()):
        if not (p/'idVendor').exists():
            continue
        row = {'path': p.name}
        for key in ('idVendor', 'idProduct', 'product', 'bDeviceClass', 'bNumConfigurations'):
            if (p/key).exists():
                row[key] = (p/key).read_text().strip()
        row['interfaces'] = []
        for q in sorted(p.glob(p.name+':*')):
            entry = {'path': q.name}
            for key in ('bInterfaceClass', 'bInterfaceSubClass', 'bInterfaceProtocol', 'bNumEndpoints'):
                if (q/key).exists():
                    entry[key] = (q/key).read_text().strip()
            row['interfaces'].append(entry)
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send-debug-event', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if hashlib.sha256(STOCK.read_bytes()).hexdigest() != '25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48':
        raise ValueError('Stock hash mismatch')
    root = ET.fromstring(gzip.decompress(CONFIG.read_bytes()))
    events = [e for e in root.iter() if e.get('key') == 'Enable USB Debug']
    if not events or any(int(e.get('value'), 0) != 0x109 for e in events):
        raise ValueError('Stock event definition mismatch')
    if not args.send_debug_event:
        print('Offline evidence checked. Prepared packet:', EVENT.hex())
        return
    if args.output is None:
        parser.error('--output required for hardware probe')
    result = {'eventPacket': EVENT.hex(), 'eventSent': False, 'transactions': [],
              'usbBefore': usb_inventory()}
    with args.output.open('x') as capture:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(5)
        try:
            sock.connect((bluetooth_address(), 1))
            gaia = Gaia(sock, result['transactions'])
            if gaia.query(0x0494, 0x0280) != bytes.fromhex('00000500050000'):
                raise ValueError('Expected firmware5.5.0 not confirmed')
            # Reference SEND_APPLICATION_MESSAGE does not send an ACK on success.
            sock.sendall(EVENT)
            result['eventSent'] = True
            time.sleep(2)
            result['postVersionReply'] = gaia.query(0x0494, 0x0280).hex()
            time.sleep(6)
        except Exception as error:
            result['error'] = str(error)
        finally:
            sock.close()
            result['usbAfter'] = usb_inventory()
            result['usbInventoryChanged'] = result['usbAfter'] != result['usbBefore']
            json.dump(result, capture, indent=2); capture.write('\n')
            print(json.dumps({k:v for k,v in result.items() if k not in ('transactions','usbBefore','usbAfter')}, indent=2))


if __name__ == '__main__':
    main()
