#!/usr/bin/env bash
set -euo pipefail

# Creates local, inert recovery media. It never calls adb, opens Bluetooth, or
# invokes the OTA application.
JIELI_COMMIT="4bf054e1ae6e549b617e266cea733576c80c55d5"
APK_NAME="JLOTA_V1.9.0_10905-debug.apk"
APK_SHA256="bdbea4b7e90d42ea1eb5715575f890afe2057ec6b103a00ba5189bd41705edf5"
APK_SIZE="52293970"
APK_URL="https://raw.githubusercontent.com/Jieli-Tech/Android-JL_OTA/${JIELI_COMMIT}/apk/${APK_NAME}"

STOCK_NAME="HP206_UGREEN_Studio_Pro_V0.2.9.ufw"
STOCK_SHA256="41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6"
STOCK_SIZE="2181056"
STOCK_PATH="${1:-artifacts/original/firmware/${STOCK_NAME}}"
OUTPUT_DIR="${2:-artifacts/recovery-kit}"

for command_name in curl jq sha256sum stat; do
    command -v "$command_name" >/dev/null || {
        echo "Saknar program: $command_name" >&2
        exit 1
    }
done

verify_file() {
    local path="$1"
    local expected_size="$2"
    local expected_sha="$3"
    local actual_size actual_sha
    actual_size="$(stat -c '%s' "$path")"
    actual_sha="$(sha256sum "$path" | awk '{print $1}')"
    [[ "$actual_size" == "$expected_size" ]] || {
        echo "Fel storlek för $path: $actual_size (väntade $expected_size)" >&2
        return 1
    }
    [[ "$actual_sha" == "$expected_sha" ]] || {
        echo "Fel SHA-256 för $path: $actual_sha" >&2
        return 1
    }
}

[[ -f "$STOCK_PATH" ]] || {
    echo "Saknar officiell stock-firmware: $STOCK_PATH" >&2
    echo "Kör ./tools/fetch_official_firmware.sh först." >&2
    exit 1
}
verify_file "$STOCK_PATH" "$STOCK_SIZE" "$STOCK_SHA256"

mkdir -p "$OUTPUT_DIR"
work_dir="$(mktemp -d -t eutherblue-recovery.XXXXXX)"
trap 'rm -rf -- "$work_dir"' EXIT

curl --fail --location --show-error --max-time 300 --retry 2 \
    "$APK_URL" --output "$work_dir/$APK_NAME"
verify_file "$work_dir/$APK_NAME" "$APK_SIZE" "$APK_SHA256"

cp -- "$work_dir/$APK_NAME" "$OUTPUT_DIR/$APK_NAME"
cp -- "$STOCK_PATH" "$OUTPUT_DIR/$STOCK_NAME"

jq -n \
    --arg createdAt "$(date --iso-8601=seconds)" \
    --arg apk "$APK_NAME" \
    --arg apkSha256 "$APK_SHA256" \
    --arg apkSource "$APK_URL" \
    --arg jieLiCommit "$JIELI_COMMIT" \
    --arg stock "$STOCK_NAME" \
    --arg stockSha256 "$STOCK_SHA256" \
    '{
        createdAt: $createdAt,
        purpose: "inert Android stock-recovery media",
        writesDevice: false,
        apk: {
            file: $apk,
            sha256: $apkSha256,
            source: $apkSource,
            upstreamCommit: $jieLiCommit,
            packageName: "com.jieli.otasdk",
            upstreamVersionName: "1.9.0"
        },
        stockFirmware: {
            file: $stock,
            sha256: $stockSha256,
            productVersion: "0.2.9"
        },
        warning: "Prepared only. Installing the APK does not authorize starting OTA."
    }' > "$OUTPUT_DIR/manifest.json"

verify_file "$OUTPUT_DIR/$APK_NAME" "$APK_SIZE" "$APK_SHA256"
verify_file "$OUTPUT_DIR/$STOCK_NAME" "$STOCK_SIZE" "$STOCK_SHA256"

echo "Återställningskit förberett utan installation eller OTA: $OUTPUT_DIR"
echo "APK SHA-256:   $APK_SHA256"
echo "Stock SHA-256: $STOCK_SHA256"
