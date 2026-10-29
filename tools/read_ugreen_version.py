#!/usr/bin/env python3
"""Read the product firmware version from a UGREEN headset over Bluetooth SPP.

Safety boundary: this program contains one fixed outbound UG1 packet: GET_VERSION.
It has no arbitrary-send, configuration-write, OTA, or firmware-transfer API.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import socket
import sys
from pathlib import Path
from typing import Any

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib


BLUEZ_SERVICE = "org.bluez"
PROFILE_INTERFACE = "org.bluez.Profile1"
PROFILE_MANAGER_INTERFACE = "org.bluez.ProfileManager1"
DEVICE_INTERFACE = "org.bluez.Device1"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"
PROFILE_PATH = "/se/eutherblue/readonly_ugreen_version_profile"


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
            crc &= 0xFFFF
    return crc


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def build_get_version() -> bytes:
    body = bytes((0x01, 0x01, 0x00))
    crc = crc16_modbus(body)
    return b"\xAA\xBB\xCC" + body + crc.to_bytes(2, "little")


GET_VERSION = build_get_version()
assert GET_VERSION == bytes.fromhex("AA BB CC 01 01 00 21 90")


def extract_frames(data: bytes) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    offset = 0
    while True:
        start = data.find(b"\xDD\xEE\xFF", offset)
        if start < 0 or start + 8 > len(data):
            break
        data_length = data[start + 5]
        end = start + 6 + data_length + 2
        if end > len(data):
            break
        raw = data[start:end]
        expected_crc = int.from_bytes(raw[-2:], "little")
        # UGREEN's UG1 protocol uses Modbus CRC for app requests but
        # CCITT-FALSE for device responses. Both are serialized little-endian.
        calculated_crc = crc16_ccitt_false(raw[3:-2])
        payload = raw[6:-2]
        frame: dict[str, Any] = {
            "rawHex": raw.hex(),
            "command": raw[3],
            "responseFlag": raw[4],
            "success": bool(raw[4]),
            "dataLength": data_length,
            "dataHex": payload.hex(),
            "expectedCrc": f"0x{expected_crc:04x}",
            "calculatedCrc": f"0x{calculated_crc:04x}",
            "crcValid": expected_crc == calculated_crc,
        }
        if raw[3] == 0x01 and raw[4] != 0 and len(payload) >= 3:
            primary = payload[:3]
            fallback = payload[3:6]
            chosen = primary if any(primary) else fallback
            if len(chosen) == 3:
                frame["firmwareVersion"] = ".".join(str(part) for part in chosen)
                frame["versionSource"] = "primary" if chosen == primary else "fallback"
        frames.append(frame)
        offset = end
    return frames


def find_device_path(bus: dbus.SystemBus, address: str) -> str:
    manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE, "/"), OBJECT_MANAGER_INTERFACE)
    for path, interfaces in manager.GetManagedObjects().items():
        device = interfaces.get(DEVICE_INTERFACE)
        if device and str(device.get("Address", "")).upper() == address.upper():
            return str(path)
    raise RuntimeError(f"BlueZ hittar inte enheten {address}")


class VersionProfile(dbus.service.Object):
    def __init__(self, bus: dbus.SystemBus, loop: GLib.MainLoop, timeout_seconds: float):
        super().__init__(bus, PROFILE_PATH)
        self.loop = loop
        self.timeout_seconds = timeout_seconds
        self.raw_response = b""
        self.bytes_sent = 0
        self.error: str | None = None
        self.connected_device: str | None = None

    @dbus.service.method(PROFILE_INTERFACE, in_signature="", out_signature="")
    def Release(self) -> None:
        if self.loop.is_running():
            self.loop.quit()

    @dbus.service.method(PROFILE_INTERFACE, in_signature="oha{sv}", out_signature="")
    def NewConnection(self, device: dbus.ObjectPath, fd: dbus.UnixFd, properties: dict) -> None:
        del properties
        self.connected_device = str(device)
        connection = socket.socket(fileno=fd.take())
        connection.settimeout(self.timeout_seconds)
        try:
            connection.sendall(GET_VERSION)
            self.bytes_sent = len(GET_VERSION)
            chunks = bytearray()
            while len(chunks) < 65536:
                try:
                    chunk = connection.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.extend(chunk)
                frames = extract_frames(bytes(chunks))
                if any(
                    frame["command"] == 1 and frame["success"] and frame["crcValid"]
                    for frame in frames
                ):
                    break
            self.raw_response = bytes(chunks)
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
        finally:
            connection.close()
            if self.loop.is_running():
                self.loop.quit()

    @dbus.service.method(PROFILE_INTERFACE, in_signature="o", out_signature="")
    def RequestDisconnection(self, device: dbus.ObjectPath) -> None:
        self.connected_device = str(device)


def run_query(address: str, timeout_seconds: float) -> dict[str, Any]:
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    loop = GLib.MainLoop()
    profile = VersionProfile(bus, loop, timeout_seconds)
    profile_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, "/org/bluez"), PROFILE_MANAGER_INTERFACE
    )
    device_path = find_device_path(bus, address)
    device = dbus.Interface(bus.get_object(BLUEZ_SERVICE, device_path), DEVICE_INTERFACE)
    options = {
        "Name": dbus.String("EutherBlue read-only UGREEN version probe"),
        "Role": dbus.String("client"),
        "RequireAuthentication": dbus.Boolean(False),
        "RequireAuthorization": dbus.Boolean(False),
        "AutoConnect": dbus.Boolean(False),
    }
    registered = False
    connect_error: list[str] = []
    try:
        profile_manager.RegisterProfile(PROFILE_PATH, SPP_UUID, options)
        registered = True

        def connected() -> None:
            return None

        def failed(error: Exception) -> None:
            connect_error.append(str(error))
            if loop.is_running():
                loop.quit()

        device.ConnectProfile(SPP_UUID, reply_handler=connected, error_handler=failed)
        GLib.timeout_add(int((timeout_seconds + 3) * 1000), lambda: loop.quit() or False)
        loop.run()
    finally:
        if registered:
            try:
                profile_manager.UnregisterProfile(PROFILE_PATH)
            except dbus.DBusException:
                pass

    frames = extract_frames(profile.raw_response)
    matches = [
        frame
        for frame in frames
        if frame["command"] == 1
        and frame["success"]
        and frame["crcValid"]
        and "firmwareVersion" in frame
    ]
    return {
        "capturedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "address": address.upper(),
        "transport": "Bluetooth Classic SPP",
        "serviceUuid": SPP_UUID,
        "safety": {
            "operation": "UGREEN UG1 GET_VERSION only",
            "requestHex": GET_VERSION.hex(),
            "bytesSent": profile.bytes_sent,
            "writeOrOtaCommandsAvailable": False,
        },
        "devicePath": profile.connected_device or device_path,
        "rawResponseHex": profile.raw_response.hex(),
        "frames": frames,
        "firmwareVersion": matches[0]["firmwareVersion"] if matches else None,
        "versionResponseFound": bool(matches),
        "error": profile.error or (connect_error[0] if connect_error else None),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only UGREEN product-version probe over SPP")
    parser.add_argument("--address", required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--query",
        action="store_true",
        help="perform the single GET_VERSION query; without this flag nothing is sent",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", args.address):
        parser.error("ogiltig Bluetooth-adress")
    if not 1.0 <= args.timeout <= 30.0:
        parser.error("--timeout måste vara mellan 1 och 30 sekunder")
    if not args.query:
        print("Dry-run: inget skickades.")
        print(f"Tillåtet UGREEN-paket: {GET_VERSION.hex(' ')}")
        return 0

    result = run_query(args.address, args.timeout)
    output = args.output
    if output is None:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        output = Path("artifacts/captures") / f"ugreen-version-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Sparat: {output}", file=sys.stderr)
    return 0 if result["versionResponseFound"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
