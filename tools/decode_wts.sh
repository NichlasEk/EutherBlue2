#!/usr/bin/env bash
set -euo pipefail

SDK_COMMIT="fdc018de81629e21e594d677cf05f87d288be0f0"
TOOL_URL="https://raw.githubusercontent.com/Jieli-Tech/fw-AC63_BT_SDK/$SDK_COMMIT/cpu/bd19/tools/AC632N_config_tool/conf/source/tone/wtgv2_decode.exe"
TOOL_SHA256="d9388e8eedb7a3b4295d1f524c347e70512412ac54712e1737196f8380ff663b"
EXTRACTED="${1:-artifacts/extracted/studio-pro-v0.2.9}"
OUTPUT="${2:-$EXTRACTED/decoded}"
CACHE_DIR="${EUTHERBLUE_CACHE_DIR:-.cache}"
DECODER="$CACHE_DIR/jieli-tone-tools/wtgv2_decode.exe"

for command_name in curl sha256sum wine winepath find; do
    command -v "$command_name" >/dev/null || {
        echo "Saknar program: $command_name" >&2
        exit 1
    }
done
[[ -d "$EXTRACTED/files/tone_en-extracted" ]] || {
    echo "Extraherade promptfiler saknas under: $EXTRACTED" >&2
    exit 1
}

mkdir -p "$(dirname "$DECODER")" "$OUTPUT"
export WINEDEBUG=-all
if [[ ! -f "$DECODER" ]]; then
    curl --fail --location --silent --show-error --max-time 60 \
        "$TOOL_URL" \
        --output "$DECODER"
fi
echo "$TOOL_SHA256  $DECODER" | sha256sum --check --status || {
    echo "JieLi-avkodarens SHA256 stämmer inte." >&2
    exit 1
}

decoded=0
while IFS= read -r -d '' source_file; do
    language="$(basename "$(dirname "$source_file")" -extracted)"
    destination_dir="$OUTPUT/$language"
    destination_file="$destination_dir/$(basename "${source_file%.wts}").wav"
    mkdir -p "$destination_dir"
    wine "$DECODER" \
        "$(winepath -w "$source_file")" \
        "$(winepath -w "$destination_file")" >/dev/null 2>&1
    [[ -s "$destination_file" ]] || {
        echo "Avkodningen misslyckades för: $source_file" >&2
        exit 1
    }
    decoded=$((decoded + 1))
done < <(find "$EXTRACTED/files" -type f -path '*tone_*-extracted/*.wts' -print0)

echo "Avkodade $decoded röstprompter till: $OUTPUT"
