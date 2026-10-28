#!/usr/bin/env python3
"""Run extracted reference HandleReady with instrumented stubs, entirely offline.

This tests reference control flow, not flash behavior, firmware acceptance,
or the ROM's bank-swap checks. No Bluetooth/USB code is used.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('artifacts/research/hd350bt')
SOURCE = ROOT/'adk642-reference/apps/libs/upgrade/upgrade_sm.c'
ELF = ROOT/'adk642-reference/sink.elf'
STOCK = Path('artifacts/extracted/hd350bt/firmware-5.5.0/HD350_firmware_v5.5.0.bin')
OUT = ROOT/'source-search/resume-harness'


def audit_apply_gate():
    path = ROOT/'adk642-reference/apps/libs/upgrade/CONFIG_HYDRACORE/upgrade_sm_config.c'
    text = path.read_text()
    begin = text.index('static void IsValidatedToTrySwap(bool reset)\n{')
    end = text.index('\n/*\nNAME\n    UpgradeSMAbort', begin)
    functions = text[begin:end]
    prelude = r'''
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
#include <stddef.h>
typedef unsigned char uint8;
#define TRUE true
#define FALSE false
#define PRINT(x) do {} while(0)
typedef unsigned MessageId;
typedef void *Message;
typedef struct { bool isCsrValidDoneReqReceived; } UpgradeCtx;
typedef struct { unsigned action; } UPGRADE_HOST_TRANSFER_COMPLETE_RES_T;
enum { UPGRADE_INTERNAL_CONTINUE=1, UPGRADE_HOST_TRANSFER_COMPLETE_RES,
 UPGRADE_HOST_IS_CSR_VALID_DONE_REQ, UPGRADE_INTERNAL_REBOOT,
 UPGRADE_VM_IMAGE_UPGRADE_COPY_SUCCESSFUL, UPGRADE_VM_DFU_COPY_VALIDATION_SUCCESS,
 UPGRADE_VM_AUDIO_DFU_FAILURE, UPGRADE_VM_IMAGE_UPGRADE_COPY_FAILED };
enum { UPGRADE_HOST_TRANSFER_COMPLETE_IND=1, UPGRADE_RESUME_POINT_POST_REBOOT=3,
 UPGRADE_APPLY_IND=8, UPGRADE_STATE_SYNC=10,
 upgrade_end_state_complete=20, upgrade_end_state_abort=21 };
static UpgradeCtx ctx;
static struct { unsigned upgrade_in_progress_key; } keys;
static unsigned shutdown_calls, swap_calls, ps_saves, indications;
static UpgradeCtx *UpgradeCtxGet(void) { return &ctx; }
#define UpgradeCtxGetPSKeys() (&keys)
static void UpgradeApplyAudioShutDown(void) { shutdown_calls++; }
static void UpgradeHostIFDataSendShortMsg(unsigned x) { (void)x;indications++; }
static void UpgradeSavePSKeys(void) { ps_saves++; }
static void UpgradeSendEndUpgradeDataInd(unsigned x) { (void)x; }
static bool UpgradeSMHavePermissionToProceed(unsigned x) { (void)x;return true; }
static void UpgradeSMMoveToState(unsigned x) { (void)x; }
static void ImageUpgradeSwapTry(void) { swap_calls++; }
static void UpgradeApplyAudioCopyFailed(void) {}
'''
    tests = r'''
int main(void) {
 UPGRADE_HOST_TRANSFER_COMPLETE_RES_T accept={.action=0};
 IsValidatedToTrySwap(true);
 assert(UpgradeSMHandleValidated(UPGRADE_HOST_TRANSFER_COMPLETE_RES,&accept));
 assert(shutdown_calls==0 && swap_calls==0);
 assert(UpgradeSMHandleValidated(UPGRADE_HOST_TRANSFER_COMPLETE_RES,&accept));
 assert(shutdown_calls==1 && swap_calls==0);
 printf("{\"repeatedHostAccepts\":2,\"copySuccessEvents\":0,\"audioShutdownCalls\":%u,\"swapCallsBeforeCallback\":%u,\"psSaveCalls\":%u}\n",
        shutdown_calls,swap_calls,ps_saves);
 /* This callback is simulated, NOT demonstrated on the physical headset. */
 assert(UpgradeSMHandleValidated(UPGRADE_VM_DFU_COPY_VALIDATION_SUCCESS,NULL));
 assert(swap_calls==1);
 printf("{\"simulatedAudioValidationCallback\":true,\"swapTrapCalls\":%u}\n",swap_calls);
 return 0;
}
'''
    harness = OUT/'apply_gate.c'
    harness.write_text(prelude+functions+tests)
    binary = OUT/'apply_gate'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
                    '-Wno-implicit-fallthrough',str(harness),'-o',str(binary)],check=True)
    run = subprocess.run([str(binary)],check=True,capture_output=True,text=True)
    return {'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'scope':'Extracted reference C; permission granted by stub; audio callback simulated',
            'cases':[json.loads(line) for line in run.stdout.splitlines()],
            'conclusion':'The reference counter does not distinguish repeated host accepts from copy-success events. Real audio/ROM validation remains unresolved.'}


def main():
    from elftools.elf.elffile import ELFFile
    firmware = STOCK.read_bytes()
    if hashlib.sha256(firmware).hexdigest() != '25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48':
        raise ValueError('Unexpected stock firmware')
    with ELF.open('rb') as f:
        elf = ELFFile(f)
        syms = list(elf.get_section_by_name('.symtab').iter_symbols())
        sym = next(s for s in syms if s.name == '_HandleReady')
        end = min(s['st_value'] for s in syms if s['st_info']['type'] == 'STT_FUNC'
                  and s.name.startswith(('_', '$_')) and s['st_value'] > sym['st_value'])
        sec = elf.get_section(sym['st_shndx'])
        start = sym['st_value'] - sec['sh_addr']
        code = sec.data()[start:start+end-sym['st_value']]
        if len(code) != 120 or code != firmware[0x14d5c4:0x14d5c4+120]:
            raise ValueError('Exact HandleReady match missing')
    source = SOURCE.read_text()
    function = source[source.index('bool HandleReady(MessageId id, Message message)\n{'):
                      source.index('bool HandleProhibited(MessageId id, Message message)\n{')]
    prelude = r'''
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
#define TRUE true
#define FALSE false
typedef unsigned MessageId;
typedef void *Message;
#define UNUSED(x) (void)(x)
#define PRINT(x) do {} while(0)
enum { UPGRADE_HOST_START_REQ=1, UPGRADE_HOST_ERROR_INTERNAL_ERROR_4=99 };
enum { UPGRADE_RESUME_POINT_START, UPGRADE_RESUME_POINT_PRE_VALIDATE,
 UPGRADE_RESUME_POINT_PRE_REBOOT, UPGRADE_RESUME_POINT_POST_REBOOT,
 UPGRADE_RESUME_POINT_COMMIT, UPGRADE_RESUME_POINT_ERASE, UPGRADE_RESUME_POINT_ERROR };
enum { UPGRADE_STATE_DATA_READY=10, UPGRADE_STATE_VALIDATING,
 UPGRADE_STATE_VALIDATED, UPGRADE_STATE_COMMIT_HOST_CONTINUE,
 UPGRADE_STATE_COMMIT, UPGRADE_STATE_ABORTING };
static struct { unsigned upgrade_in_progress_key; } keys;
#define UpgradeCtxGetPSKeys() (&keys)
static unsigned state, partition_starts, validation_inits, moved, ack, fatal;
static void UpgradeSMSetState(unsigned s) { state=s; }
static void UpgradeSMMoveToState(unsigned s) { state=s; moved++; }
static void UpgradePartitionValidationInit(void) { validation_inits++; }
static void UpgradePartitionsUpgradeStarted(void) { partition_starts++; }
static void UpgradeHostIFDataSendStartCfm(unsigned a,unsigned b) { (void)a;(void)b;ack++; }
static void FatalError(unsigned a) { (void)a;fatal++; }
'''
    tests = r'''
int main(void) {
 for (unsigned resume=0;resume<3;resume++) {
  keys.upgrade_in_progress_key=resume;
  state=partition_starts=validation_inits=moved=ack=fatal=0;
  assert(HandleReady(UPGRADE_HOST_START_REQ,NULL));
  assert(ack==1 && fatal==0);
  if(resume==0) assert(state==UPGRADE_STATE_DATA_READY && partition_starts==1);
  if(resume==1) assert(state==UPGRADE_STATE_VALIDATING && validation_inits==1 && partition_starts==1);
  if(resume==2) assert(state==UPGRADE_STATE_VALIDATED && partition_starts==0 && validation_inits==0 && moved==0);
  printf("{\"resume\":%u,\"state\":%u,\"partitionStarts\":%u,\"validationInitialisations\":%u,\"moveCalls\":%u}\n",
   resume,state,partition_starts,validation_inits,moved);
 }
 return 0;
}
'''
    OUT.mkdir(parents=True, exist_ok=True)
    harness = OUT/'handle_ready.c'
    harness.write_text(prelude+function+tests)
    binary = OUT/'handle_ready'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(harness),'-o',str(binary)],check=True)
    run = subprocess.run([str(binary)],check=True,capture_output=True,text=True)
    result = {'scope':'Extracted reference C with instrumented stubs, not physical flash validation',
              'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'stockExactMatch':{'fileOffset':'0x14d5c4','bytes':120},
              'cases':[json.loads(line) for line in run.stdout.splitlines()],
              'conclusion':'PRE_REBOOT selects VALIDATED without calling partition-start or validation-init in HandleReady.',
              'unresolved':['Preparing a valid inactive bank','ROM and copy validation','Safe recovery after interrupted flash','Physical acceptance of edited prompts']}
    result['applyGate'] = audit_apply_gate()
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
