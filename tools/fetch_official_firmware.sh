#!/usr/bin/env bash
set -euo pipefail

API_URL="https://api3.ugreeniot.com/app/v1/software/version/check_upgrade"
SERIAL_NO="studio_pro_ota"
MODEL_NAME="UGREEN Studio Pro"
OUTPUT_DIR="${1:-artifacts/original/firmware}"

for command_name in curl jq md5sum sha256sum stat; do
    command -v "$command_name" >/dev/null || {
        echo "Saknar program: $command_name" >&2
        exit 1
    }
done

mkdir -p "$OUTPUT_DIR"
work_dir="$(mktemp -d -t eutherblue-fetch.XXXXXX)"
trap 'rm -rf -- "$work_dir"' EXIT

metadata="$work_dir/metadata.json"
curl --fail --silent --show-error --max-time 30 \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    --data "{\"versionCode\":0,\"versionName\":\"$MODEL_NAME\",\"serialNo\":\"$SERIAL_NO\"}" \
    "$API_URL" \
    --output "$metadata"

jq -e --arg serial "$SERIAL_NO" \
    '.code == 100000 and .success == true and .data.softwareSerialNo == $serial and (.data.fileUrl | length > 0)' \
    "$metadata" >/dev/null

file_url="$(jq -r '.data.fileUrl' "$metadata")"
file_name="$(jq -r '.data.fileName' "$metadata")"
expected_md5="$(jq -r '.data.fileMd5 | ascii_downcase' "$metadata")"
expected_size="$(jq -r '.data.fileSize' "$metadata")"
target="$OUTPUT_DIR/$file_name"

curl --fail --location --show-error --max-time 180 --retry 2 \
    "$file_url" \
    --output "$target.part"

actual_size="$(stat -c '%s' "$target.part")"
actual_md5="$(md5sum "$target.part" | awk '{print $1}')"

if [[ "$actual_size" != "$expected_size" ]]; then
    echo "Fel filstorlek: väntade $expected_size, fick $actual_size" >&2
    exit 1
fi
if [[ "$actual_md5" != "$expected_md5" ]]; then
    echo "MD5 stämmer inte: väntade $expected_md5, fick $actual_md5" >&2
    exit 1
fi

mv -- "$target.part" "$target"

# Spara reproducerbar metadata men utelämna den kortlivade signerade URL:en.
jq --arg sourceApi "$API_URL" \
    '.data.fileUrl = null | . + {sourceApi: $sourceApi}' \
    "$metadata" > "$OUTPUT_DIR/$file_name.metadata.json"

echo "Hämtad och verifierad: $target"
echo "MD5:    $actual_md5"
echo "SHA256: $(sha256sum "$target" | awk '{print $1}')"
