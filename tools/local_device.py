"""Explicit local device selection; no personal Bluetooth addresses in source."""
import os
import re


def bluetooth_address(variable="EUTHERBLUE_HD350_ADDRESS"):
    value = os.environ.get(variable, "").strip().upper()
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", value) or value == "00:00:00:00:00:00":
        raise ValueError(f"Set {variable} to your headset Bluetooth address before connecting")
    return value
