#!/usr/bin/env python3
"""Run existing guarded apply tools, then commit on the first charging HID.

Requires an already verified resume-2 capture. Never re-arms by itself.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage-capture', type=Path, required=True)
    p.add_argument('--resume-capture', type=Path, required=True)
    p.add_argument('--device', required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    from apply_hd350_staged_candidate_usb import evidence_guard
    evidence_guard(a.stage_capture, a.resume_capture)
    if not a.execute:
        print('Guards passed; plan: first apply, second apply, charging HID commit. No device opened.')
        return
    a.output_dir.mkdir(exist_ok=False)
    common = ['--stage-capture', str(a.stage_capture), '--resume-capture', str(a.resume_capture)]

    def run(script, arguments, name, required):
        output = a.output_dir / (name + '.json')
        print(datetime.now(timezone.utc).isoformat(), name, flush=True)
        subprocess.run([sys.executable, str(Path(__file__).parent / script),
                        *arguments, '--execute', '--output', str(output)], check=True)
        result = json.loads(output.read_text())
        if 'error' in result or not result.get(required):
            raise RuntimeError(f'{name} stopped: {result.get("error", "missing success evidence")}')
        return output

    first = run('apply_hd350_staged_candidate_usb.py',
                [a.device, *common], 'first', 'transferCompleteResponsesSent')
    run('send_hd350_second_transfer_complete_usb.py',
        [a.device, '--apply-capture', str(first)], 'second', 'usbDisconnectedAfterSecondApply')
    run('commit_hd350_post_reboot_usb.py',
        [*common, '--hid-id', 'charging', '--wait-seconds', '20'], 'commit', 'completed')


if __name__ == '__main__':
    main()
