#!/usr/bin/env python3
"""Empty-socket-only, fixed 30-second VDD selector-0 measurement window.

Uses the existing EutherCharge Open-TL866 client; does not flash firmware.
Host cleanup cannot guarantee shutdown after USB failure: unplug USB then.
"""
import argparse
import signal
import time
from pathlib import Path

PORT = '/dev/serial/by-id/usb-ProgHQ_Open-TL866_Programmer_80921F18DB5377744FCF06D5-if00'
SETUP = [('i', ()), ('v', (0,)), ('g', ('0000008000',)),
         ('d', ('0000000001',)), ('e', (1,))]
OFF = [('d', ('0000000000',)), ('E', (0,)), ('e', (0,)), ('i', ())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--empty-socket-meter-ready', action='store_true')
    args = parser.parse_args()
    if not args.empty_socket_meter_ready:
        print('Offline plan only. Empty ZIF, no adapters or ICSP cables.')
        print('Red meter lead: ZIF1. Black: ZIF16. DC volts, NOT current mode.')
        print('Setup:', SETUP, '\nAfter 30 seconds:', OFF)
        return
    if not Path(PORT).exists():
        raise RuntimeError('Expected programmer is absent')
    from otl866.aclient import AClient

    class BitbangClient(AClient):
        APP = 'bitbang'

    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    client = BitbangClient(PORT)
    try:
        for command, arguments in SETUP:
            print(command, arguments, client.cmd(command, *arguments), flush=True)
        print('MEASURE NOW: ZIF1 positive, ZIF16 ground; 30 seconds.', flush=True)
        time.sleep(30)
    finally:
        failures = []
        for command, arguments in OFF:
            try:
                print('Shutdown:', command, client.cmd(command, *arguments), flush=True)
            except Exception as exc:
                failures.append(str(exc))
            if command == 'd':
                time.sleep(0.5)
        client.ser.close()
        if failures:
            raise RuntimeError('UNPLUG USB: shutdown unconfirmed: ' + '; '.join(failures))
        print('Shutdown acknowledged. Check meter; physical decay is not measured by software.')


if __name__ == '__main__':
    main()
