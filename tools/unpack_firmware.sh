#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/kagaimiq/jl-misctools.git"
PINNED_COMMIT="0a5b12db0ef38f3042acffbe2452730a37fd2405"
FIRMWARE="${1:-artifacts/original/firmware/HP206_UGREEN_Studio_Pro_V0.2.9.ufw}"
OUTPUT="${2:-artifacts/extracted/studio-pro-v0.2.9}"
CACHE_DIR="${EUTHERBLUE_CACHE_DIR:-.cache}"
TOOLS_DIR="$CACHE_DIR/jl-misctools"
VENV_DIR="$CACHE_DIR/fw-venv"

for command_name in git python; do
    command -v "$command_name" >/dev/null || {
        echo "Saknar program: $command_name" >&2
        exit 1
    }
done
[[ -f "$FIRMWARE" ]] || {
    echo "Firmwarefilen saknas: $FIRMWARE" >&2
    echo "Kör först: ./tools/fetch_official_firmware.sh" >&2
    exit 1
}
[[ ! -e "$OUTPUT" ]] || {
    echo "Målkatalogen finns redan: $OUTPUT" >&2
    echo "Välj en ny katalog eller flytta den gamla manuellt." >&2
    exit 1
}

mkdir -p "$CACHE_DIR"
if [[ ! -d "$TOOLS_DIR/.git" ]]; then
    git clone --quiet "$REPO_URL" "$TOOLS_DIR"
fi
git -C "$TOOLS_DIR" fetch --quiet origin "$PINNED_COMMIT"
git -C "$TOOLS_DIR" checkout --quiet --detach "$PINNED_COMMIT"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    python -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet crcmod PyYAML
fi

"$VENV_DIR/bin/python" "$TOOLS_DIR/firmware/fwunpack_newfw.py" \
    --dirname "$(realpath -m "$OUTPUT")" \
    "$(realpath "$FIRMWARE")"

[[ -s "$OUTPUT/jlfw.yaml" && -d "$OUTPUT/files/tone_en-extracted" ]] || {
    echo "Uppackningen gav inte väntad firmwarestruktur." >&2
    exit 1
}
echo "Uppackat skrivskyddat till: $OUTPUT"
