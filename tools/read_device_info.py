#!/usr/bin/env python3
"""Read JieLi target information over Bluetooth SPP.

Safety boundary: this program contains exactly one outbound RCSP packet,
GetTargetInfo(mask=0xffffffff, platform=0). It has no arbitrary-send or OTA API.
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
PROFILE_PATH = "/se/eutherblue/readonly_spp_profile"

# FE DC BA | command+response flag, opcode 3, parameter length 6 |
# sequence 0, mask ffffffff, platform 0 | EF
GET_TARGET_INFO = bytes.fromhex("FE DC BA C0 03 00 06 00 FF FF FF FF 00 EF")


def version_name(version_code: int) -> str:
    return "V_{}.{}.{}.{}".format(
        (version_code >> 12) & 0xF,
        (version_code >> 8) & 0xF,
        (version_code >> 4) & 0xF,
        version_code & 0xF,
    )


def bluetooth_address(data: bytes) -> str:
    return ":".join(f"{part:02X}" for part in data)


def parse_target_info(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"attributes": []}
    offset = 0
    while offset + 2 <= len(data):
        encoded_length = data[offset]
        attr_type = data[offset + 1]
        data_length = encoded_length - 1
        end = offset + 2 + data_length
        if encoded_length < 1 or end > len(data):
            result["parseWarning"] = f"invalid TLV at offset {offset}"
            break
        value = data[offset + 2 : end]
        result["attributes"].append(
            {"type": attr_type, "length": data_length, "hex": value.hex()}
        )

        if attr_type == 0 and value:
            result["protocolVersion"] = f"V_{value[0] >> 4}.{value[0] & 0x0F}"
        elif attr_type == 1 and len(value) >= 3:
            result["quantity"] = value[0]
            result["volume"] = value[1]
            result["maxVolume"] = value[2]
            if len(value) >= 5:
                result["lowPowerLimit"] = value[4]
        elif attr_type == 2 and len(value) >= 6:
            result["edrAddress"] = bluetooth_address(value[:6])
            if len(value) >= 8:
                result["edrProfile"] = value[6]
                result["edrStatus"] = value[7]
        elif attr_type == 4 and len(value) >= 5:
            result["functionMask"] = int.from_bytes(value[:4], "big")
            result["currentFunction"] = value[4]
        elif attr_type == 5 and len(value) >= 2:
            code = int.from_bytes(value[:2], "big")
            result["versionCode"] = code
            result["versionName"] = version_name(code)
        elif attr_type == 6 and value:
            result["sdkType"] = value[0]
        elif attr_type == 8 and value:
            result["supportsDoubleBackup"] = value[0] == 1
            if len(value) >= 2:
                result["needsBootLoader"] = value[1] == 1
            if len(value) >= 3:
                result["singleBackupOtaWay"] = value[2]
        elif attr_type == 9 and value:
            result["mandatoryUpgradeFlag"] = value[0]
            if len(value) >= 2:
                result["requestOtaFlag"] = value[1]
            if len(value) >= 3:
                result["expandMode"] = value[2]
        elif attr_type == 10 and len(value) >= 4:
            result["vid"] = int.from_bytes(value[:2], "big")
            result["pid"] = int.from_bytes(value[2:4], "big")
            result["uid"] = int.from_bytes(value[4:6], "big") if len(value) >= 6 else result["vid"]
        elif attr_type == 11:
            result["authKey"] = value.decode("utf-8", errors="replace")
        elif attr_type == 12:
            result["projectCode"] = value.decode("utf-8", errors="replace")
        elif attr_type == 13 and len(value) >= 2:
            result["receiveMtu"] = int.from_bytes(value[:2], "big")
            if len(value) >= 4:
                result["communicationMtu"] = int.from_bytes(value[2:4], "big")
        elif attr_type == 14 and value:
            result["allowConnectFlag"] = value[0]
        elif attr_type == 16:
            result["name"] = value.decode("utf-8", errors="replace")
        elif attr_type == 17 and value:
            result["bleOnly"] = value[0] == 1
            if len(value) >= 7:
                result["bleAddress"] = bluetooth_address(value[1:7])
        elif attr_type == 19 and value:
            result["supportsMd5"] = bool(value[0] & 0x01)
            result["gameMode"] = bool(value[0] & 0x02)
        elif attr_type == 31:
            result["customVersionMessage"] = value.decode("utf-8", errors="replace")
        offset = end
    return result


def extract_frames(data: bytes) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    offset = 0
    while True:
        start = data.find(b"\xFE\xDC\xBA", offset)
        if start < 0 or start + 8 > len(data):
            break
        parameter_length = int.from_bytes(data[start + 5 : start + 7], "big")
        frame_length = parameter_length + 8
        end = start + frame_length
        if end > len(data):
            break
        raw = data[start:end]
        payload = raw[7:-1]
        frame: dict[str, Any] = {
            "rawHex": raw.hex(),
            "flags": raw[3],
            "type": (raw[3] >> 7) & 1,
            "hasResponse": (raw[3] >> 6) & 1,
            "opcode": raw[4],
            "parameterLength": parameter_length,
            "trailerValid": raw[-1] == 0xEF,
        }
        if frame["type"] == 0 and len(payload) >= 2:
            frame["status"] = payload[0]
            frame["sequence"] = payload[1]
            frame["parameterHex"] = payload[2:].hex()
            if frame["opcode"] == 3 and frame["status"] == 0:
                frame["targetInfo"] = parse_target_info(payload[2:])
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


class ReadOnlyProfile(dbus.service.Object):
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
        descriptor = fd.take()
        connection = socket.socket(fileno=descriptor)
        connection.settimeout(self.timeout_seconds)
        try:
            connection.sendall(GET_TARGET_INFO)
            self.bytes_sent = len(GET_TARGET_INFO)
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
                if any(frame.get("type") == 0 and frame.get("opcode") == 3 for frame in frames):
                    break
            self.raw_response = bytes(chunks)
        except Exception as exc:  # preserve the diagnostic in the JSON capture
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
    profile = ReadOnlyProfile(bus, loop, timeout_seconds)
    profile_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE, "/org/bluez"), PROFILE_MANAGER_INTERFACE
    )
    device_path = find_device_path(bus, address)
    device = dbus.Interface(bus.get_object(BLUEZ_SERVICE, device_path), DEVICE_INTERFACE)
    options = {
        "Name": dbus.String("EutherBlue read-only RCSP probe"),
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
    matching = [frame for frame in frames if frame.get("type") == 0 and frame.get("opcode") == 3]
    return {
        "capturedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "address": address.upper(),
        "transport": "Bluetooth Classic SPP",
        "serviceUuid": SPP_UUID,
        "safety": {
            "operation": "GetTargetInfo only",
            "requestHex": GET_TARGET_INFO.hex(),
            "bytesSent": profile.bytes_sent,
            "otaCommandsAvailable": False,
        },
        "devicePath": profile.connected_device or device_path,
        "rawResponseHex": profile.raw_response.hex(),
        "frames": frames,
        "targetInfoResponseFound": bool(matching),
        "error": profile.error or (connect_error[0] if connect_error else None),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only JieLi RCSP target-info probe over SPP")
    parser.add_argument("--address", default="00:00:00:00:00:00")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--query",
        action="store_true",
        help="perform the single GetTargetInfo query; without this flag nothing is sent",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", args.address):
        parser.error("ogiltig Bluetooth-adress")
    if not 1.0 <= args.timeout <= 30.0:
        parser.error("--timeout måste vara mellan 1 och 30 sekunder")
    if not args.query:
        print("Dry-run: inget skickades.")
        print(f"Tillåtet RCSP-paket: {GET_TARGET_INFO.hex(' ')}")
        return 0

    result = run_query(args.address, args.timeout)
    output = args.output
    if output is None:
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        output = Path("artifacts/captures") / f"target-info-{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Sparat: {output}", file=sys.stderr)
    return 0 if result["targetInfoResponseFound"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
