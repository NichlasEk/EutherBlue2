#!/usr/bin/env python3
"""Build an UNSIGNED OFFLINE ONLY voice experiment; never talks to a headset."""
import hashlib
import json
from pathlib import Path
from verify_hd350_signature import parse, load_key, verify


def main():
    base = Path('artifacts/extracted/hd350bt')
    stock = (base/'firmware-5.5.0/HD350_firmware_v5.5.0.bin').read_bytes()
    if hashlib.sha256(stock).hexdigest() != '25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48':
        raise ValueError('Unexpected original firmware')
    inventory = json.loads((base/'inspection-5.5.0/inventory.json').read_text())
    block = next(b for b in inventory['blocks'] if b.get('partition') == 7)
    entry = next(f for f in block['files'] if f['path'] == 'prompts/10.prm')
    parts, positions, _ = parse(stock)
    start = positions[7] + entry['offset']
    end = start + entry['size']
    original = stock[start:end]
    if hashlib.sha256(original).hexdigest() != entry['sha256']:
        raise ValueError('Original prompt mismatch')
    replacement = Path('artifacts/build/hd350bt-offline-resource/10.prm').read_bytes()
    if len(replacement) != len(original) or len(replacement) % 128:
        raise ValueError('Replacement must preserve the exact SBC file size')
    candidate = stock[:start] + replacement + stock[end:]
    new_parts, new_positions, new_signature = parse(candidate)
    if new_positions != positions or any(new_parts[n] != parts[n] for n in parts if n != 7):
        raise ValueError('Unexpected layout or non-resource change')
    trust = (base/'firmware-5.8.0/HD350BT_firmware_v580_DFU.bin').read_bytes()
    key = load_key(trust)
    if not verify(stock, key)['signatureValid'] or verify(candidate, key)['signatureValid']:
        raise ValueError('Unexpected signature result')
    out = Path('artifacts/build/hd350bt-UNSIGNED-OFFLINE-ONLY')
    out.mkdir(parents=True, exist_ok=True)
    image = out/'HD350BT-5.5.0-power-on-UNSIGNED-OFFLINE-ONLY.bin'
    if image.exists() and image.read_bytes() != candidate:
        raise ValueError('Different candidate already exists')
    image.write_bytes(candidate)
    manifest = {'status':'UNSIGNED OFFLINE ONLY; NOT flash-ready; no device transfer',
                'file':str(image), 'size':len(candidate),
                'sha256':hashlib.sha256(candidate).hexdigest(),
                'stockSha256':hashlib.sha256(stock).hexdigest(),
                'signatureValid':False, 'audiblyAccepted':False,
                'onlyChangedFile':'prompts/10.prm', 'fileOffset':start,
                'resourceBytes':len(replacement),
                'changedBytes':sum(a != b for a,b in zip(original,replacement)),
                'originalResourceSha256':entry['sha256'],
                'replacementSha256':hashlib.sha256(replacement).hexdigest(),
                'allOtherBytesIdentical':candidate[:start] == stock[:start] and candidate[end:] == stock[end:]}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    main()
