#!/usr/bin/env bash
set -euo pipefail

SDK_COMMIT="fdc018de81629e21e594d677cf05f87d288be0f0"
SDK_ROOT="https://raw.githubusercontent.com/Jieli-Tech/fw-AC63_BT_SDK/$SDK_COMMIT/cpu/bd19/tools/AC632N_config_tool/conf/source/tone"
ENCODER_SHA256="43cd39a0728918ca87accb5d6616cb3025211969df0a8d31e0286491ad53eb92"
RESAMPLER_SHA256="9a4d8234851c9a5a4fd29c151166b5ad641e4e7856e0cc6ad0b76e53364d4273"
DECODER_SHA256="d9388e8eedb7a3b4295d1f524c347e70512412ac54712e1737196f8380ff663b"
INPUT="${1:-artifacts/previews/christian-grosshandlare-irriterad/full-bank}"
OUTPUT="${2:-artifacts/build/christian-grosshandlare-irriterad/wts}"
BITRATE="${EUTHERBLUE_WTS_BITRATE:-12000}"
TEMPO_MAP="${EUTHERBLUE_WTS_TEMPO_MAP:-}"
EXPECTED_PROMPTS="${EUTHERBLUE_EXPECTED_PROMPTS:-20}"
CACHE_DIR="${EUTHERBLUE_CACHE_DIR:-.cache}"
TOOLS_DIR="$CACHE_DIR/jieli-tone-tools"
ENCODER="$TOOLS_DIR/wtgv2_encode.exe"
RESAMPLER="$TOOLS_DIR/wtgv2_resample.exe"
DECODER="$TOOLS_DIR/wtgv2_decode.exe"

for command_name in curl ffmpeg find sha256sum wine winepath; do
    command -v "$command_name" >/dev/null || {
        echo "Saknar program: $command_name" >&2
        exit 1
    }
done
[[ "$BITRATE" =~ ^[0-9]+$ ]] && (( BITRATE >= 8000 && BITRATE <= 24000 )) || {
    echo "EUTHERBLUE_WTS_BITRATE måste vara 8000–24000." >&2
    exit 1
}
[[ "$EXPECTED_PROMPTS" =~ ^[1-9][0-9]*$ ]] || {
    echo "EUTHERBLUE_EXPECTED_PROMPTS måste vara ett positivt heltal." >&2
    exit 1
}
[[ -d "$INPUT" ]] || {
    echo "Provbanken saknas: $INPUT" >&2
    exit 1
}
mkdir -p "$TOOLS_DIR" "$OUTPUT" "$OUTPUT/decoded-check"

declare -A TEMPO_FACTORS=()
if [[ -n "$TEMPO_MAP" ]]; then
    [[ -f "$TEMPO_MAP" ]] || {
        echo "Tempokartan saknas: $TEMPO_MAP" >&2
        exit 1
    }
    while read -r prompt factor extra; do
        [[ -z "${prompt:-}" || "$prompt" == \#* ]] && continue
        [[ -z "${extra:-}" && "$factor" =~ ^[0-9]+([.][0-9]+)?$ ]] || {
            echo "Ogiltig rad i tempokartan: $prompt ${factor:-} ${extra:-}" >&2
            exit 1
        }
        TEMPO_FACTORS["$prompt"]="$factor"
    done < "$TEMPO_MAP"
fi

fetch_tool() {
    local name="$1"
    local destination="$2"
    local expected_sha="$3"
    if [[ ! -f "$destination" ]]; then
        curl --fail --location --silent --show-error --max-time 60 \
            "$SDK_ROOT/$name" --output "$destination"
    fi
    echo "$expected_sha  $destination" | sha256sum --check --status || {
        echo "Fel SHA256 för JieLi-verktyget: $destination" >&2
        exit 1
    }
}

fetch_tool "wtgv2_encode.exe" "$ENCODER" "$ENCODER_SHA256"
fetch_tool "wtgv2_resample.exe" "$RESAMPLER" "$RESAMPLER_SHA256"
fetch_tool "wtgv2_decode.exe" "$DECODER" "$DECODER_SHA256"

temp_dir="$(mktemp -d /tmp/eutherblue-wts-encode.XXXXXX)"
trap 'rm -r -- "$temp_dir"' EXIT
export WINEDEBUG=-all
encoded=0
total_bytes=0
while IFS= read -r -d '' source_file; do
    prompt="$(basename "$source_file" -16k-stereo.wav)"
    pcm_32k="$temp_dir/$prompt-32k.raw"
    pcm_16k="$temp_dir/$prompt-16k.raw"
    destination="$OUTPUT/$prompt.wts"
    decoded="$OUTPUT/decoded-check/$prompt.wav"
    tempo="${TEMPO_FACTORS[$prompt]:-1.0}"
    ffmpeg_args=(-hide_banner -loglevel error -y -i "$source_file")
    if [[ "$tempo" != "1" && "$tempo" != "1.0" ]]; then
        ffmpeg_args+=(-filter:a "atempo=$tempo")
    fi
    ffmpeg "${ffmpeg_args[@]}" -ar 32000 -ac 1 -f s16le \
        -acodec pcm_s16le "$pcm_32k"
    wine "$RESAMPLER" "$(winepath -w "$pcm_32k")" "$(winepath -w "$pcm_16k")" \
        >/dev/null 2>&1
    wine "$ENCODER" "$(winepath -w "$pcm_16k")" "$(winepath -w "$destination")" \
        o.raw "$BITRATE" 16000 20 0 1 >/dev/null 2>&1
    wine "$DECODER" "$(winepath -w "$destination")" "$(winepath -w "$decoded")" \
        >/dev/null 2>&1
    [[ -s "$destination" && -s "$decoded" ]] || {
        echo "WTS-roundtrip misslyckades för: $prompt" >&2
        exit 1
    }
    size="$(stat -c %s "$destination")"
    total_bytes=$((total_bytes + size))
    encoded=$((encoded + 1))
    printf '%-14s %6d byte  tempo %s\n' "$prompt" "$size" "$tempo"
done < <(find "$INPUT" -maxdepth 1 -type f -name '*-16k-stereo.wav' -print0 | sort -z)

[[ "$encoded" -eq "$EXPECTED_PROMPTS" ]] || {
    echo "Väntade $EXPECTED_PROMPTS prompter men kodade $encoded." >&2
    exit 1
}
echo "Kodade $encoded WTS-filer vid $BITRATE bit/s, totalt $total_bytes byte: $OUTPUT"
