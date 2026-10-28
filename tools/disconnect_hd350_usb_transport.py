#!/usr/bin/env python3
"""Send only HD 350BT HID upgrade transport DISCONNECT (feature command 7)."""
import argparse
import os
from pathlib import Path

from read_hd350_upgrade_identity import command
from stage_hd350_unsigned_candidate_usb import identify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', type=Path)
    args = parser.parse_args()
    identify(args.device)
    journal = []
    fd = os.open(args.device, os.O_RDWR | os.O_NONBLOCK)
    try:
        command(fd, 7, journal)
    finally:
        os.close(fd)
    print({'device': str(args.device), 'transportDisconnectSent': True,
           'upgradeAbortSent': False, 'journal': journal})


if __name__ == '__main__':
    main()
