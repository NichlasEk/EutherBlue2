#!/usr/bin/env bash
set -euo pipefail

# Offline voice-resource experiment only. This script contains no Bluetooth,
# firmware packing, flash, erase, OTA, serial, or USB-device operation.
CONFIG="voice-banks/christian-grosshandlare-irriterad-bth13.json"
TEMPO_MAP="voice-banks/christian-grosshandlare-irriterad-bth13.tempo"
LAYOUT="profiles/linocell-bth13/reference-tone-layout.json"
PREVIEWS="artifacts/previews/christian-grosshandlare-irriterad-bth13/full-bank"
OUTPUT="artifacts/build/christian-grosshandlare-irriterad-bth13/wts-reference-fit"

python3 tools/generate_voice_bank.py \
    --config "$CONFIG" \
    --output-dir "$PREVIEWS"

EUTHERBLUE_WTS_BITRATE=8000 \
EUTHERBLUE_EXPECTED_PROMPTS=16 \
EUTHERBLUE_WTS_TEMPO_MAP="$TEMPO_MAP" \
    tools/encode_voice_bank_wts.sh "$PREVIEWS" "$OUTPUT"

python3 tools/validate_wts_bank.py "$OUTPUT" "$LAYOUT"

echo "Offline BTH13 reference bank passed. No device was contacted."
