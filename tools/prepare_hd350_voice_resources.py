#!/usr/bin/env python3
"""Fit natural-speed TTS prompts into the stock HD 350BT SBC slots.

Only leading/trailing silence is removed. Speech is never time-compressed or
truncated. Each output is padded back to the exact stock duration so the
firmware filesystem metadata remains byte-for-byte unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import wave
from array import array
from pathlib import Path


RATE = 16_000
SBC_FRAME_SAMPLES = 128
SBC_FRAME_BYTES = 128


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_mono_s16(path: Path) -> list[int]:
    with wave.open(str(path), "rb") as source:
        actual = (
            source.getnchannels(),
            source.getsampwidth(),
            source.getframerate(),
            source.getcomptype(),
        )
        if actual != (2, 2, RATE, "NONE"):
            raise ValueError(f"unexpected WAV format in {path}: {actual}")
        frames = source.getnframes()
        samples = array("h", source.readframes(frames))
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) != frames * 2:
        raise ValueError(f"short stereo WAV data in {path}")
    return [(samples[index] + samples[index + 1]) // 2 for index in range(0, len(samples), 2)]


def active_span(samples: list[int]) -> tuple[int, int, float, float]:
    window = RATE // 100  # 10 ms
    rms_values: list[float] = []
    for start in range(0, len(samples), window):
        block = samples[start : start + window]
        rms_values.append(math.sqrt(sum(value * value for value in block) / len(block)))
    peak_rms = max(rms_values, default=0.0)
    threshold = max(16.0, peak_rms * 0.01)  # -40 dB relative, with a low absolute floor
    active = [index for index, value in enumerate(rms_values) if value >= threshold]
    if not active:
        raise ValueError("no audible samples found")
    pre_roll = round(RATE * 0.024)
    post_roll = round(RATE * 0.048)
    start = max(0, active[0] * window - pre_roll)
    end = min(len(samples), (active[-1] + 1) * window + post_roll)
    return start, end, peak_rms, threshold


def write_mono_s16(path: Path, samples: list[int]) -> None:
    data = array("h", samples)
    if sys.byteorder != "little":
        data.byteswap()
    with wave.open(str(path), "wb") as destination:
        destination.setnchannels(1)
        destination.setsampwidth(2)
        destination.setframerate(RATE)
        destination.writeframes(data.tobytes())


def encode_sbc(source: Path, destination: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            str(RATE),
            "-c:a",
            "sbc",
            "-f",
            "sbc",
            str(destination),
        ],
        check=True,
    )


def validate_sbc(path: Path, frames: int, expected_size: int) -> None:
    data = path.read_bytes()
    if len(data) != expected_size or len(data) != frames * SBC_FRAME_BYTES:
        raise ValueError(f"wrong SBC size in {path}: {len(data)} != {expected_size}")
    for index in range(frames):
        frame = data[index * SBC_FRAME_BYTES : (index + 1) * SBC_FRAME_BYTES]
        if frame[:3] != b"\x9c\x31\x3c":
            raise ValueError(f"wrong SBC header in {path}, frame {index}: {frame[:3].hex()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--layout", type=Path, default=Path("artifacts/previews/hd350bt-stock-5.8.0/layout.json")
    )
    parser.add_argument(
        "--config", type=Path, default=Path("voice-banks/christian-grosshandlare-hd350bt.json")
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("artifacts/previews/christian-grosshandlare-hd350bt/full-bank"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/build/hd350bt-christian-grosshandlare-resources"),
    )
    args = parser.parse_args()

    layout = {int(item["id"]): item for item in json.loads(args.layout.read_text())}
    config = json.loads(args.config.read_text())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "status": "offline resources; natural speed; no firmware or device operation",
        "config": str(args.config),
        "layout": str(args.layout),
        "speechTempoChanged": False,
        "fitMethod": "trim leading/trailing silence, retain 24 ms pre-roll and up to 48 ms post-roll, then zero-pad",
        "prompts": {},
    }

    for prompt_id in sorted(layout):
        slot = layout[prompt_id]
        source = args.input_dir / f"{prompt_id}-16k-stereo.wav"
        samples = read_mono_s16(source)
        start, end, peak_rms, threshold = active_span(samples)
        speech = samples[start:end]
        target_samples = int(slot["frames"]) * SBC_FRAME_SAMPLES
        if len(speech) > target_samples:
            excess_ms = (len(speech) - target_samples) * 1000 / RATE
            raise ValueError(
                f"prompt {prompt_id} does not fit at natural speed: "
                f"{len(speech) / RATE:.3f}s > {target_samples / RATE:.3f}s by {excess_ms:.1f}ms"
            )
        fitted = speech + [0] * (target_samples - len(speech))
        fitted_wav = args.output_dir / f"{prompt_id}-fitted-natural.wav"
        output_prm = args.output_dir / f"{prompt_id}.prm"
        write_mono_s16(fitted_wav, fitted)
        encode_sbc(fitted_wav, output_prm)
        validate_sbc(output_prm, int(slot["frames"]), int(slot["size"]))
        prompt = config["prompts"][str(prompt_id)]
        manifest["prompts"][str(prompt_id)] = {
            "event": prompt["event"],
            "text": prompt["text"],
            "source": str(source),
            "sourceSha256": sha256(source),
            "sourceSeconds": len(samples) / RATE,
            "trimmedNaturalSeconds": len(speech) / RATE,
            "slotSeconds": target_samples / RATE,
            "paddingSeconds": (target_samples - len(speech)) / RATE,
            "peakRms": round(peak_rms, 3),
            "trimThresholdRms": round(threshold, 3),
            "fittedWav": str(fitted_wav),
            "sbc": str(output_prm),
            "sbcBytes": output_prm.stat().st_size,
            "sbcFrames": int(slot["frames"]),
            "sbcSha256": sha256(output_prm),
            "tempoChanged": False,
            "speechTruncated": False,
        }
        print(
            f"{prompt_id:2}: {prompt['text']:<22} "
            f"speech={len(speech) / RATE:.3f}s slot={target_samples / RATE:.3f}s "
            f"pad={(target_samples - len(speech)) / RATE:.3f}s"
        )

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
