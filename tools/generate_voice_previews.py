#!/usr/bin/env python3
"""Generate local Christian Grosshandlare headset voice previews via EutherLink.

This only creates WAV files under artifacts/previews. It never opens a Bluetooth
connection and contains no firmware packing or flashing operation.
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
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINT = "http://127.0.0.1:8765"
DEFAULT_REFERENCE = Path(
    "~/EutherVox/models/moss-reference/stormakt3020/"
    "christian-grosshandlare-calm-b.wav"
)
REFERENCE_TEXT = (
    "Välkommen till mitt kontor. Christian Grosshandlare är namnet. "
    "Jag köper god vara, säljer till rätt pris och håller ordning på varje "
    "tunna och krona. Ge mig fakta i lugn ton, så skall du få ett klart "
    "besked och en affär som håller."
)
VARIANTS = (
    {
        "slug": "irriterad",
        "text": "Den är ansluten, för fan, mannen!",
        "seed": 206025,
    },
    {
        "slug": "rasande",
        "text": "DEN ÄR ANSLUTEN! För fan, mannen!",
        "seed": 206029,
    },
    {
        "slug": "handelspsykotisk",
        "text": "Den är ansluten! FÖR FAN, mannen!",
        "seed": 206099,
    },
)


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
    status_url = urllib.parse.urljoin(endpoint + "/", str(accepted["status_url"]).lstrip("/"))
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = request_json(status_url)
        state = str(status.get("status", ""))
        if state == "done":
            return status
        if state in {"failed", "cancelled"}:
            raise RuntimeError(f"TTS-jobb {accepted['id']} slutade som {state}: {status.get('error')}")
        print(f"{accepted['id']}: {state} {status.get('message', '')}", flush=True)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate three local UGREEN voice previews")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/previews/christian-grosshandlare/bt_conn"),
    )
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    if not args.reference.is_file():
        parser.error(f"referensrösten saknas: {args.reference}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reference_base64 = base64.b64encode(args.reference.read_bytes()).decode("ascii")

    accepted_jobs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for variant in VARIANTS:
        payload = {
            "text": variant["text"],
            "language": "sv",
            "model_backend": "voxcpm2",
            "output_format": "wav",
            "reference_wav_base64": reference_base64,
            "prompt_text": REFERENCE_TEXT,
            "cfg_value": 2.0,
            "inference_timesteps": 20,
            "normalize": False,
            "seed": variant["seed"],
        }
        accepted = request_json(args.endpoint.rstrip("/") + "/v1/tts/jobs", payload)
        accepted_jobs.append((variant, accepted))
        print(f"Skickade {variant['slug']}: {accepted['id']}", flush=True)

    manifest: dict[str, Any] = {
        "character": "Christian Grosshandlare",
        "event": "bt_conn",
        "reference": str(args.reference),
        "referenceSha256": sha256(args.reference),
        "firmwareWritten": False,
        "variants": [],
    }
    for variant, accepted in accepted_jobs:
        status = wait_for_job(args.endpoint.rstrip("/"), accepted, args.timeout)
        source = args.output_dir / f"bt_conn-{variant['slug']}-source.wav"
        headset = args.output_dir / f"bt_conn-{variant['slug']}-16k-stereo.wav"
        audio_url = urllib.parse.urljoin(
            args.endpoint.rstrip("/") + "/", str(accepted["audio_url"]).lstrip("/")
        )
        download(audio_url, source)
        convert_for_headset(source, headset)
        manifest["variants"].append(
            {
                **variant,
                "jobId": accepted["id"],
                "source": str(source),
                "sourceSha256": sha256(source),
                "headsetPreview": str(headset),
                "headsetPreviewSha256": sha256(headset),
                "status": status.get("status"),
            }
        )
        print(f"Klar: {headset}", flush=True)

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        raise SystemExit(f"Fel: {exc}") from exc
