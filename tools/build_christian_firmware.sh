#!/usr/bin/env bash
set -euo pipefail

ORIGINAL_UFW="${1:-artifacts/original/firmware/HP206_UGREEN_Studio_Pro_V0.2.9.ufw}"
EXTRACTED="${2:-artifacts/extracted/studio-pro-v0.2.9}"
PREVIEWS="${3:-artifacts/previews/christian-grosshandlare-irriterad/full-bank}"
OUTPUT="${4:-artifacts/build/christian-grosshandlare-irriterad}"
FIRMWARE="$OUTPUT/HP206_UGREEN_Studio_Pro_V0.2.9_Christian-BOOTCRC-v4-WORKING.ufw"
BITRATE="${EUTHERBLUE_WTS_BITRATE:-8000}"
TEMPO_MAP="${EUTHERBLUE_WTS_TEMPO_MAP:-voice-banks/christian-grosshandlare-irriterad-fixed-layout.tempo}"

for required in \
    "$ORIGINAL_UFW" \
    "$EXTRACTED/decrypted.bin" \
    "$EXTRACTED/files/tone_en" \
    "$PREVIEWS/bt_conn-16k-stereo.wav"; do
    [[ -f "$required" ]] || {
        echo "Saknar byggindata: $required" >&2
        exit 1
    }
done
[[ -x .cache/fw-venv/bin/python && -f .cache/jl-misctools/firmware/fwunpack_newfw.py ]] || {
    echo "Saknar den pinnade uppackarmiljön; kör ./tools/unpack_firmware.sh först." >&2
    exit 1
}

mkdir -p "$OUTPUT" "$OUTPUT/roundtrip"
EUTHERBLUE_WTS_BITRATE="$BITRATE" EUTHERBLUE_WTS_TEMPO_MAP="$TEMPO_MAP" \
    ./tools/encode_voice_bank_wts.sh "$PREVIEWS" "$OUTPUT/wts-v3-fixed"
./tools/repack_tone_library.py \
    "$EXTRACTED/files/tone_en" \
    "$OUTPUT/roundtrip/tone_en" \
    --require-identical \
    --manifest "$OUTPUT/roundtrip/tone_en.manifest.json" >/dev/null
./tools/repack_tone_library.py \
    "$EXTRACTED/files/tone_en" \
    "$OUTPUT/tone_en" \
    --replacements "$OUTPUT/wts-v3-fixed" \
    --preserve-layout \
    --manifest "$OUTPUT/tone_en.manifest.json" >/dev/null
./tools/build_custom_firmware.py \
    --original-ufw "$ORIGINAL_UFW" \
    --decrypted-flash "$EXTRACTED/decrypted.bin" \
    --original-tone "$EXTRACTED/files/tone_en" \
    --replacement-tone "$EXTRACTED/files/tone_en" \
    --output "$OUTPUT/roundtrip/HP206-roundtrip.ufw" \
    --manifest "$OUTPUT/roundtrip/HP206-roundtrip.manifest.json" \
    --require-identical >/dev/null
./tools/build_custom_firmware.py \
    --original-ufw "$ORIGINAL_UFW" \
    --decrypted-flash "$EXTRACTED/decrypted.bin" \
    --original-tone "$EXTRACTED/files/tone_en" \
    --replacement-tone "$OUTPUT/tone_en" \
    --output "$FIRMWARE" \
    --manifest "$OUTPUT/firmware.manifest.json" >/dev/null

validation_parent="$(mktemp -d /tmp/eutherblue-fw-validation.XXXXXX)"
trap 'rm -r -- "$validation_parent"' EXIT
validation_dir="$validation_parent/unpacked"
.cache/fw-venv/bin/python .cache/jl-misctools/firmware/fwunpack_newfw.py \
    --dirname "$(realpath -m "$validation_dir")" \
    "$(realpath "$FIRMWARE")" >"$OUTPUT/validation-unpack.log" 2>&1
[[ -f "$validation_dir/files/tone_en" ]] || {
    echo "Den oberoende uppackaren återfann inte tone_en." >&2
    exit 1
}
cmp "$OUTPUT/tone_en" "$validation_dir/files/tone_en"
./tools/repack_tone_library.py \
    "$validation_dir/files/tone_en" \
    "$validation_parent/tone_en-roundtrip" \
    --preserve-layout \
    --require-identical >/dev/null

original_sha="$(sha256sum "$ORIGINAL_UFW" | cut -d ' ' -f 1)"
roundtrip_sha="$(sha256sum "$OUTPUT/roundtrip/HP206-roundtrip.ufw" | cut -d ' ' -f 1)"
firmware_sha="$(sha256sum "$FIRMWARE" | cut -d ' ' -f 1)"
[[ "$original_sha" == "$roundtrip_sha" ]] || {
    echo "Hel-UFW-roundtrippen är inte byte-identisk." >&2
    exit 1
}

echo "Byte-identisk original-roundtrip: $roundtrip_sha"
echo "Modifierad, oflashad firmware:     $firmware_sha"
echo "Fil: $FIRMWARE"
