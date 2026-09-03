#!/usr/bin/env bash
set -euo pipefail

PROFILE_ID="${1:-hp206-jl708n}"
PROFILE_TOOL="./tools/eutherblue.py"

get_profile() {
    "$PROFILE_TOOL" get "$PROFILE_ID" "$1"
}

"$PROFILE_TOOL" check "$PROFILE_ID"

DRIVER="$(get_profile build.driver)"
[[ "$DRIVER" == "jieli-ufw-boot-crc-v1" ]] || {
    echo "Byggdrivrutinen stöds inte av detta skript: $DRIVER" >&2
    exit 1
}

ORIGINAL_UFW="$(get_profile firmware.stock.path)"
DECRYPTED_FLASH="$(get_profile firmware.decryptedFlashPath)"
ORIGINAL_TONE="$(get_profile voice.originalPath)"
VOICE_CONTAINER="$(get_profile voice.container)"
PREVIEWS="$(get_profile voice.previewPath)"
OUTPUT="$(get_profile build.outputDirectory)"
FIRMWARE="$OUTPUT/$(get_profile build.outputFilename)"
BITRATE="$(get_profile voice.bitrate)"
TEMPO_MAP="$(get_profile voice.tempoMap)"
PROMPT_COUNT="$(get_profile voice.promptCount)"
EXPECTED_SHA="$(get_profile build.verifiedSha256)"
BOOT_INFO_OFFSET="$(get_profile firmware.banks.bootInfo.offset)"
BOOT_INFO_SIZE="$(get_profile firmware.banks.bootInfo.size)"
BOOT_DATA_CRC_OFFSET="$(get_profile firmware.banks.bootInfo.dataCrcOffset)"
BOOT_DATA_LENGTH_OFFSET="$(get_profile firmware.banks.bootInfo.dataLengthOffset)"
BOOT_CIPHER_KEY="$(get_profile firmware.banks.bootInfo.cipherKey)"
WTS_OUTPUT="$OUTPUT/wts-$PROFILE_ID"
ROUNDTRIP="$OUTPUT/roundtrip/$PROFILE_ID-roundtrip.ufw"

for required in \
    "$ORIGINAL_UFW" \
    "$DECRYPTED_FLASH" \
    "$ORIGINAL_TONE" \
    "$PREVIEWS/bt_conn-16k-stereo.wav" \
    "$TEMPO_MAP"; do
    [[ -f "$required" ]] || {
        echo "Saknar byggindata: $required" >&2
        exit 1
    }
done
[[ -x .cache/fw-venv/bin/python && -f .cache/jl-misctools/firmware/fwunpack_newfw.py ]] || {
    echo "Saknar den pinnade uppackarmiljön; kör ./tools/unpack_firmware.sh först." >&2
    exit 1
}

actual_prompts="$(find "$PREVIEWS" -maxdepth 1 -type f -name '*-16k-stereo.wav' | wc -l)"
[[ "$actual_prompts" -eq "$PROMPT_COUNT" ]] || {
    echo "Profilen väntar $PROMPT_COUNT röstfiler men hittade $actual_prompts." >&2
    exit 1
}

mkdir -p "$OUTPUT" "$OUTPUT/roundtrip"
EUTHERBLUE_WTS_BITRATE="$BITRATE" \
EUTHERBLUE_WTS_TEMPO_MAP="$TEMPO_MAP" \
EUTHERBLUE_EXPECTED_PROMPTS="$PROMPT_COUNT" \
    ./tools/encode_voice_bank_wts.sh "$PREVIEWS" "$WTS_OUTPUT"
./tools/repack_tone_library.py \
    "$ORIGINAL_TONE" \
    "$OUTPUT/roundtrip/$VOICE_CONTAINER" \
    --require-identical \
    --manifest "$OUTPUT/roundtrip/tone_en.manifest.json" >/dev/null
./tools/repack_tone_library.py \
    "$ORIGINAL_TONE" \
    "$OUTPUT/$VOICE_CONTAINER" \
    --replacements "$WTS_OUTPUT" \
    --preserve-layout \
    --manifest "$OUTPUT/tone_en.manifest.json" >/dev/null

boot_args=(
    --boot-info-offset "$BOOT_INFO_OFFSET"
    --boot-info-size "$BOOT_INFO_SIZE"
    --boot-info-data-crc-offset "$BOOT_DATA_CRC_OFFSET"
    --boot-info-data-length-offset "$BOOT_DATA_LENGTH_OFFSET"
    --boot-info-cipher-key "$BOOT_CIPHER_KEY"
)
./tools/build_custom_firmware.py \
    --original-ufw "$ORIGINAL_UFW" \
    --decrypted-flash "$DECRYPTED_FLASH" \
    --original-tone "$ORIGINAL_TONE" \
    --replacement-tone "$ORIGINAL_TONE" \
    --output "$ROUNDTRIP" \
    --manifest "$OUTPUT/roundtrip/firmware.manifest.json" \
    --require-identical \
    "${boot_args[@]}" >/dev/null
./tools/build_custom_firmware.py \
    --original-ufw "$ORIGINAL_UFW" \
    --decrypted-flash "$DECRYPTED_FLASH" \
    --original-tone "$ORIGINAL_TONE" \
    --replacement-tone "$OUTPUT/$VOICE_CONTAINER" \
    --output "$FIRMWARE" \
    --manifest "$OUTPUT/firmware.manifest.json" \
    "${boot_args[@]}" >/dev/null

validation_parent="$(mktemp -d /tmp/eutherblue-fw-validation.XXXXXX)"
trap 'rm -r -- "$validation_parent"' EXIT
validation_dir="$validation_parent/unpacked"
.cache/fw-venv/bin/python .cache/jl-misctools/firmware/fwunpack_newfw.py \
    --dirname "$(realpath -m "$validation_dir")" \
    "$(realpath "$FIRMWARE")" >"$OUTPUT/validation-unpack.log" 2>&1
[[ -f "$validation_dir/files/$VOICE_CONTAINER" ]] || {
    echo "Den oberoende uppackaren återfann inte $VOICE_CONTAINER." >&2
    exit 1
}
cmp "$OUTPUT/$VOICE_CONTAINER" "$validation_dir/files/$VOICE_CONTAINER"
./tools/repack_tone_library.py \
    "$validation_dir/files/$VOICE_CONTAINER" \
    "$validation_parent/$VOICE_CONTAINER-roundtrip" \
    --preserve-layout \
    --require-identical >/dev/null

original_sha="$(sha256sum "$ORIGINAL_UFW" | cut -d ' ' -f 1)"
roundtrip_sha="$(sha256sum "$ROUNDTRIP" | cut -d ' ' -f 1)"
firmware_sha="$(sha256sum "$FIRMWARE" | cut -d ' ' -f 1)"
[[ "$original_sha" == "$roundtrip_sha" ]] || {
    echo "Hel-UFW-roundtrippen är inte byte-identisk." >&2
    exit 1
}
[[ "$firmware_sha" == "$EXPECTED_SHA" ]] || {
    echo "Byggets SHA-256 avviker från profilens fysiskt verifierade firmware." >&2
    echo "Väntade: $EXPECTED_SHA" >&2
    echo "Fick:    $firmware_sha" >&2
    exit 1
}

echo "Profil:                          $PROFILE_ID"
echo "Byte-identisk original-roundtrip: $roundtrip_sha"
echo "Fysiskt verifierad firmware:      $firmware_sha"
echo "Fil: $FIRMWARE"
