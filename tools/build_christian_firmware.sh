#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 0 ]]; then
    echo "Den gamla positional-parameter-varianten är ersatt av modellprofiler." >&2
    echo "Kör ./tools/build_profile_firmware.sh hp206-jl708n." >&2
    exit 2
fi

exec ./tools/build_profile_firmware.sh hp206-jl708n
