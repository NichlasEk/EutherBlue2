#!/usr/bin/env python3
"""Render a configured voice bank to ordinary and headset-preview WAV files.

This tool only calls the local EutherLink TTS service and writes WAV previews.
It has no Bluetooth, WTS packing, firmware building, or flashing operation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINT = "http://127.0.0.1:8765"
DEFAULT_CONFIG = Path("voice-banks/christian-grosshandlare-irriterad.json")


def request_json(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        destination.write_bytes(response.read())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wait_for_job(endpoint: str, accepted: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    url = urllib.parse.urljoin(endpoint + "/", str(accepted["status_url"]).lstrip("/"))
    deadline = time.monotonic() + timeout_seconds
    previous_state = ""
    while time.monotonic() < deadline:
        status = request_json(url)
        state = str(status.get("status", ""))
        if state != previous_state:
            print(f"{accepted['id']}: {state} {status.get('message', '')}", flush=True)
            previous_state = state
        if state == "done":
            return status
        if state in {"failed", "cancelled"}:
            raise RuntimeError(f"TTS-jobb {accepted['id']} slutade som {state}: {status.get('error')}")
        time.sleep(2)
    raise TimeoutError(f"TTS-jobb {accepted['id']} hann inte bli klart")


def convert_for_headset(source: Path, destination: Path) -> None:
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
            "2",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            str(destination),
        ],
        check=True,
    )


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_montage(paths: list[Path], destination: Path) -> None:
    silence = b"\x00\x00" * 2 * int(16000 * 0.4)
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(16000)
        for index, path in enumerate(paths):
            with wave.open(str(path), "rb") as source:
                actual = (source.getnchannels(), source.getsampwidth(), source.getframerate())
                if actual != (2, 2, 16000):
                    raise RuntimeError(f"oväntat WAV-format i {path}: {actual}")
                output.writeframes(source.readframes(source.getnframes()))
            if index + 1 != len(paths):
                output.writeframes(silence)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a complete local headset voice bank")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--only", action="append", help="render only this prompt id; repeatable")
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    reference = Path(config["reference"]).expanduser()
    if not reference.is_file():
        parser.error(f"referensrösten saknas: {reference}")
    output_dir = args.output_dir or Path("artifacts/previews") / config["id"] / "full-bank"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    reference_base64 = base64.b64encode(reference.read_bytes()).decode("ascii")
    selected = set(args.only or config["prompts"].keys())
    unknown = selected.difference(config["prompts"])
    if unknown:
        parser.error("okända prompt-id: " + ", ".join(sorted(unknown)))

    manifest: dict[str, Any] = {
        "bankId": config["id"],
        "displayName": config["displayName"],
        "config": str(args.config),
        "reference": str(reference),
        "referenceSha256": sha256(reference),
        "firmwareWritten": False,
        "prompts": {},
    }
    save_manifest(manifest_path, manifest)

    for prompt_id, prompt in config["prompts"].items():
        if prompt_id not in selected:
            continue
        payload = {
            "text": prompt["text"],
            "language": config["language"],
            "model_backend": config["modelBackend"],
            "output_format": "wav",
            "reference_wav_base64": reference_base64,
            "prompt_text": config["referenceText"],
            "cfg_value": config["cfgValue"],
            "inference_timesteps": config["inferenceTimesteps"],
            "normalize": False,
            "seed": prompt["seed"],
        }
        accepted = request_json(args.endpoint.rstrip("/") + "/v1/tts/jobs", payload)
        print(f"Skickade {prompt_id}: {accepted['id']}", flush=True)
        status = wait_for_job(args.endpoint.rstrip("/"), accepted, args.timeout)
        source = output_dir / f"{prompt_id}-source.wav"
        headset = output_dir / f"{prompt_id}-16k-stereo.wav"
        audio_url = urllib.parse.urljoin(
            args.endpoint.rstrip("/") + "/", str(accepted["audio_url"]).lstrip("/")
        )
        download(audio_url, source)
        convert_for_headset(source, headset)
        manifest["prompts"][prompt_id] = {
            **prompt,
            "jobId": accepted["id"],
            "source": str(source),
            "sourceSha256": sha256(source),
            "headsetPreview": str(headset),
            "headsetPreviewSha256": sha256(headset),
            "status": status["status"],
        }
        save_manifest(manifest_path, manifest)
        print(f"Klar {len(manifest['prompts'])}/{len(selected)}: {headset}", flush=True)

    montage_paths = [
        Path(manifest["prompts"][prompt_id]["headsetPreview"])
        for prompt_id in config["prompts"]
        if prompt_id in manifest["prompts"]
    ]
    montage = output_dir / f"{config['id']}-provlyssning.wav"
    write_montage(montage_paths, montage)
    manifest["montage"] = str(montage)
    manifest["montageSha256"] = sha256(montage)
    save_manifest(manifest_path, manifest)
    print(f"Provlyssning: {montage}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        raise SystemExit(f"Fel: {exc}") from exc
