#!/bin/sh
# Keep the HD 350BT upgrade HID writable across its controlled USB re-enumeration.
set -eu

target_user=${SUDO_USER:-${USER:-}}
[ -n "$target_user" ] && [ "$target_user" != root ] || { echo "Run with sudo from your regular user account" >&2; exit 1; }
id "$target_user" >/dev/null

count=0
# Ten minutes covers the complete re-arm/apply/power-on/commit cycle while
# remaining narrowly scoped to the HD 350BT upgrade interface.
while [ "$count" -lt 6000 ]; do
    for uevent in /sys/class/hidraw/hidraw*/device/uevent; do
        [ -r "$uevent" ] || continue
        # The device can disappear between the readability check and either
        # read during a bank swap. Retry discovery instead of exiting on -e.
        hid_id=$(sed -n 's/^HID_ID=//p' "$uevent" 2>/dev/null) || continue
        hid_phys=$(sed -n 's/^HID_PHYS=//p' "$uevent" 2>/dev/null) || continue
        node=${uevent%/device/uevent}
        node=${node##*/}
        case "$hid_id" in
            0003:00001377:00006012|0003:00000A12:00004007)
                case "$hid_phys" in
                    */input2) setfacl -m "u:$target_user:rw" "/dev/$node" 2>/dev/null || true ;;
                esac
                ;;
        esac
    done
    count=$((count + 1))
    sleep 0.1
done
