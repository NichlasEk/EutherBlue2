#!/usr/bin/env python3
"""Bounded PS resume-state experiment, NEVER transfers firmware or swaps banks.

prepare creates temporary key4 only if absent, then reboots to reload it.
observe sends only upgrade CONNECT/SYNC/START/validation-status/DISCONNECT,
then removes this experiment's context and reboots. cleanup only removes it.
No DATA, START_DATA, TRANSFER_COMPLETE_RES, COMMIT, ABORT or ERASE packets.
Original absence is documented in the named capture; no generic key writer.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import time
from read_hd350_gaia_file import Gaia
from probe_hd350_hidden_usb_audio import check_stock

ORIGINAL = Path('artifacts/captures/hd350bt-usb/upgrade-context-read-after-restart-20261028.json')
IDENTIFIER = bytes.fromhex('45555448')
WORDS = [0] * 19
WORDS[11], WORDS[12], WORDS[13] = 0x5448, 0x4555, 2
CONTEXT = b''.join(w.to_bytes(2, 'big') for w in WORDS)


def owned(reply):
    if len(reply) != 41 or reply[:3] != bytes.fromhex('000004'):
        return False
    words = [int.from_bytes(reply[i:i+2], 'big') for i in range(3, len(reply), 2)]
    return words[11:14] == WORDS[11:14]


class ObserveGaia(Gaia):
    def __init__(self, sock, log):
        super().__init__(sock, log)
        self.seen = set()

    def vm_event(self, opcode):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            for entry in self.log:
                for raw in entry.get('frames', []):
                    frame = bytes.fromhex(raw)
                    if frame[4:8] != bytes.fromhex('000a4003'):
                        continue
                    payload = frame[8:8+frame[3]]
                    if len(payload) < 4 or payload[0] != 0x12:
                        continue
                    if raw not in self.seen:
                        self.sock.sendall(bytes.fromhex('ff010002000ac0030012'))
                        self.seen.add(raw)
                    vm = payload[1:]
                    if len(vm) != 3 + int.from_bytes(vm[1:3], 'big'):
                        raise ValueError('Malformed VM notification')
                    if vm[0] == 0x11:
                        raise ValueError('Upgrade error notification: '+vm.hex())
                    if vm[0] == opcode:
                        return vm
            # Drain only; no additional device commands while waiting.
            if len(self.buffer) >= 8:
                if self.buffer[:2] != b'\xff\x01' or self.buffer[2] & ~1:
                    raise ValueError('Unexpected frame')
                size = 8+self.buffer[3]+(self.buffer[2]&1)
                if len(self.buffer) >= size:
                    frame = bytes(self.buffer[:size]); del self.buffer[:size]
                    if frame[2]&1:
                        checksum = 0
                        for byte in frame: checksum ^= byte
                        if checksum: raise ValueError('Bad checksum')
                    self.log.append({'frames':[frame.hex()]})
                    continue
            self.sock.settimeout(max(.01, deadline-time.monotonic()))
            data = self.sock.recv(1024)
            if not data: raise EOFError('Connection closed')
            self.buffer.extend(data)
            if len(self.buffer)>8192: raise ValueError('Buffer limit')
        raise TimeoutError('Expected VM notification missing')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase', choices=('prepare','observe','cleanup'), required=True)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    check_stock()
    if json.loads(ORIGINAL.read_text())['replies']['upgradeContextKey4'] != '05':
        raise ValueError('Original absence evidence missing')
    if not a.execute:
        print('Offline only:', a.phase, 'temporary context19 words; no image-transfer/bank-swap commands')
        return
    if a.output is None: ap.error('--output required')
    r = {'phase':a.phase,'transactions':[],'replies':{},'mutationAttempted':False}
    with a.output.open('x') as f:
        def save():
            f.seek(0); json.dump(r,f,indent=2); f.write('\n'); f.truncate(); f.flush(); os.fsync(f.fileno())
        s = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM,socket.BTPROTO_RFCOMM)
        s.settimeout(5)
        connected = False
        g = ObserveGaia(s,r['transactions'])
        def q(name,command,payload=b'',vendor=10):
            v=g.query(vendor,command,payload);r['replies'][name]=v.hex();save();return v
        def ok(name,command,payload=b''):
            v=q(name,command,payload)
            if v != b'\0':raise ValueError(name+' rejected: '+v.hex())
        def cleanup():
            key=q('cleanupKey',0x710,b'\0\4')
            if key==b'\5':return
            if not owned(key):raise ValueError('Context ownership mismatch; no deletion')
            r['mutationAttempted']=True;save()
            ok('deleteTemporaryContext',0x712,b'\0\4')
            if q('keyAfterDelete',0x710,b'\0\4')!=b'\5':raise ValueError('Deletion not verified')
            ok('resetAfterCleanup',0x202,b'\0')
        try:
            s.connect(('00:00:00:00:00:00',1))
            if q('version',0x280,vendor=0x494)!=bytes.fromhex('00000500050000'):raise ValueError('Wrong firmware')
            if q('mode',0x282)!=b'\0\0':raise ValueError('Not normal boot mode')
            before=q('keyBefore',0x710,b'\0\4')
            if a.phase=='prepare':
                if before!=b'\5':raise ValueError('Key4 exists; not overwriting')
                r['mutationAttempted']=True;save()
                # Matched GAIA handler uses ceil(protocol_words/2).
                payload=b'\0\4'+CONTEXT+b'\0'*36
                ok('storeTemporaryContext',0x712,payload)
                if q('keyReadback',0x710,b'\0\4')!=b'\0\0\4'+CONTEXT:raise ValueError('Context readback mismatch')
                ok('resetToReloadContext',0x202,b'\0')
            elif a.phase=='observe':
                if not owned(before):raise ValueError('Expected prepared context missing')
                registration=q('registerVMNotifications',0x4001,b'\x12')
                if registration not in (b'\0',b'\0\x12'):
                    raise ValueError('VM notification registration rejected')
                ok('upgradeConnect',0x640);connected=True
                ok('sync',0x642,bytes.fromhex('130004')+IDENTIFIER)
                vm=g.vm_event(0x14);r['syncEvent']=vm.hex();save()
                if len(vm)!=9 or vm[3]!=2 or vm[4:8]!=IDENTIFIER:raise ValueError('Resume point2 not confirmed; no START')
                ok('startResume',0x642,bytes.fromhex('010000'))
                started=g.vm_event(2);r['startEvent']=started.hex();save()
                if started[3]!=0:raise ValueError('START refused')
                ok('validationStatus',0x642,bytes.fromhex('160000'))
                r['validatedEvent']=g.vm_event(0x0b).hex();save()
                # Deliberately NEVER acknowledge TRANSFER_COMPLETE with VM0x0c.
                ok('upgradeDisconnect',0x641);connected=False
                cleanup()
            else:
                cleanup()
        except Exception as e:
            r['error']=str(e);save()
            if a.phase=='observe':
                try:
                    if connected:ok('errorDisconnect',0x641)
                    cleanup()
                except Exception as c:r['cleanupError']=str(c)
        finally:
            s.close();save()
    print(json.dumps({k:v for k,v in r.items() if k!='transactions'},indent=2))


if __name__ == '__main__':main()
