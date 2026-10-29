#!/usr/bin/env python3
"""Stage the pinned offline candidate into the inactive bank, stopping before APPUPFTR.

This is a physical flash write to the INACTIVE image bank. The active 5.5.0
bank is not selected or committed by this tool. It deliberately contains no
TRANSFER_COMPLETE_RES, COMMIT, ABORT, ERASE, reset, or bank-swap command.
"""
from local_device import bluetooth_address
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import time

from probe_hd350_hidden_usb_audio import check_stock
from probe_hd350_resume_state import ObserveGaia

CANDIDATE = Path('artifacts/build/hd350bt-UNSIGNED-OFFLINE-ONLY/HD350BT-5.5.0-power-on-UNSIGNED-OFFLINE-ONLY.bin')
MANIFEST = Path('artifacts/build/hd350bt-UNSIGNED-OFFLINE-ONLY/manifest.json')
FOOTER_OFFSET = 0x17A798
EXPECTED_SHA = '26db19737f84a97b754d3e0153ca6242fa9f0b1ee5c96816eda159c8e2585a14'
SESSION_ID = bytes.fromhex('26db1973')
MAX_CHUNK = 240


def packet(opcode, data=b''):
    return bytes((opcode,)) + len(data).to_bytes(2, 'big') + data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    check_stock()
    image = CANDIDATE.read_bytes()
    manifest = json.loads(MANIFEST.read_text())
    if (hashlib.sha256(image).hexdigest() != EXPECTED_SHA
            or manifest['sha256'] != EXPECTED_SHA
            or manifest['signatureValid'] is not False
            or manifest['allOtherBytesIdentical'] is not True
            or image[FOOTER_OFFSET:FOOTER_OFFSET+8] != b'APPUPFTR'):
        raise ValueError('Candidate or footer boundary mismatch')
    if not args.execute:
        print(json.dumps({'offlineGuards':'passed','candidateSha256':EXPECTED_SHA,
                          'bytesBeforeFooter':FOOTER_OFFSET,
                          'forbiddenOpcodes':[7,12,15],
                          'note':'No device opened; inactive-bank write requires --execute.'},indent=2))
        return
    if args.output is None:
        ap.error('--output required')
    result = {'candidateSha256':EXPECTED_SHA,'footerOffset':FOOTER_OFFSET,
              'transactions':[],'replies':{},'bytesSent':0,'requests':0,
              'footerSent':False,'bankSwapRequested':False,'mutationAttempted':False}
    with args.output.open('x') as capture:
        def save():
            capture.seek(0); json.dump(result,capture,indent=2); capture.write('\n')
            capture.truncate(); capture.flush(); os.fsync(capture.fileno())
        sock = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM,socket.BTPROTO_RFCOMM)
        sock.settimeout(8)
        gaia = ObserveGaia(sock,result['transactions'])
        connected = False
        def query(name,command,payload=b'',vendor=10):
            reply=gaia.query(vendor,command,payload)
            if name: result['replies'][name]=reply.hex(); save()
            return reply
        def success(name,command,payload=b''):
            reply=query(name,command,payload)
            if reply != b'\0': raise ValueError(name+' rejected: '+reply.hex())
        def event(opcode, timeout=60):
            old=gaia.sock.gettimeout(); gaia.sock.settimeout(timeout)
            try: return gaia.vm_event(opcode)
            finally: gaia.sock.settimeout(old)
        try:
            sock.connect((bluetooth_address(),1))
            if query('version',0x280,vendor=0x494)!=bytes.fromhex('00000500050000'):
                raise ValueError('Expected firmware5.5.0 not confirmed')
            if query('bootMode',0x282)!=b'\0\0': raise ValueError('Not in normal boot mode')
            if query('contextBefore',0x710,b'\0\4')!=b'\5':
                raise ValueError('Upgrade context already exists; no staging')
            registration=query('registerVMNotifications',0x4001,b'\x12')
            if registration not in (b'\0',b'\0\x12'):
                raise ValueError('Notification registration rejected')
            success('upgradeConnect',0x640); connected=True
            success('sync',0x642,packet(0x13,SESSION_ID))
            sync=event(0x14); result['syncEvent']=sync.hex(); save()
            if len(sync)!=9 or sync[3]!=0 or sync[4:8]!=SESSION_ID:
                raise ValueError('Expected fresh resume point0 not confirmed')
            success('start',0x642,packet(0x01))
            started=event(0x02); result['startEvent']=started.hex(); save()
            if len(started)!=6 or started[3]!=0: raise ValueError('START rejected')
            result['mutationAttempted']=True; save()
            success('startData',0x642,packet(0x15))
            last_report=0
            file_cursor=0
            while True:
                request=event(0x03,120)
                if len(request)!=11: raise ValueError('Malformed DATA_BYTES_REQ: '+request.hex())
                size=int.from_bytes(request[3:7],'big')
                transport_offset=int.from_bytes(request[7:11],'big')
                if not size or file_cursor>FOOTER_OFFSET or file_cursor+size>len(image):
                    raise ValueError(f'Invalid data request fileCursor={file_cursor} size={size}')
                if transport_offset != 0:
                    raise ValueError(f'Nonzero resume offset {transport_offset} in fresh transfer')
                result['requests']+=1
                result['lastRequest']={'fileOffset':file_cursor,
                                       'transportOffset':transport_offset,'size':size}
                save()
                if file_cursor==FOOTER_OFFSET:
                    result['stoppedAtFooterRequest']=True
                    break
                if file_cursor+size>FOOTER_OFFSET:
                    raise ValueError('Request crosses footer boundary; no bytes sent')
                block=image[file_cursor:file_cursor+size]
                sent=0
                while sent<len(block):
                    chunk=block[sent:sent+MAX_CHUNK]
                    # moreData=0 means the complete upgrade file has more bytes.
                    success('',0x642,packet(0x04,b'\0'+chunk))
                    sent+=len(chunk); result['bytesSent']+=len(chunk)
                file_cursor+=size
                result['fileCursor']=file_cursor
                if result['bytesSent']-last_report>=65536:
                    last_report=result['bytesSent']
                    print(json.dumps({'stagedBytes':result['bytesSent'],
                                      'percent':round(100*result['bytesSent']/FOOTER_OFFSET,1)}),flush=True)
                save()
            success('upgradeDisconnect',0x641); connected=False
            context=query('contextAfterStaging',0x710,b'\0\4')
            if len(context)<5 or context[:3]!=bytes.fromhex('000004'):
                raise ValueError('Staged context unavailable; do not continue')
            result['contextWords']=[int.from_bytes(context[i:i+2],'big')
                                    for i in range(3,len(context),2)]
            result['completed']='All pre-footer bytes accepted; footer and apply commands withheld'
        except Exception as error:
            result['error']=str(error)
            # Disconnecting the transport is non-destructive and preserves staged state.
            if connected:
                try: success('errorDisconnect',0x641)
                except Exception as disconnect_error:
                    result['disconnectError']=str(disconnect_error)
        finally:
            sock.close(); save()
    print(json.dumps({k:v for k,v in result.items() if k!='transactions'},indent=2))


if __name__=='__main__':
    main()
