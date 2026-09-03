# EutherBlue

Skrivskyddad analys av firmware och röstprompter i **UGREEN Studio Pro / HP206**.

## Bekräftat

- Headsetet använder Bluetooth Classic SPP för appstyrning och OTA. USB-C-porten exponerar ingen USB-dataenhet på datorn.
- UGREEN-appens firmware-ID för modellen är `studio_pro_ota`.
- UGREENs officiella API publicerar för närvarande `0.2.9` (`HP206_UGREEN_Studio_Pro_V0.2.9.ufw`).
- Headsetet som testats kör produkt-firmware `0.2.5`; versionen lästes över
  Bluetooth SPP med ett CRC-verifierat, skrivskyddat `GET_VERSION`-anrop.
- Paketet identifierar plattformen som `JL708N`; firmwarefamiljen benämns även `JL7083F-B412` i distribuerade paket.
- Firmwarefilsystemet innehåller separata engelska och kinesiska promptbibliotek. De engelska filerna inkluderar bland annat `power_on.wts`, `power_off.wts`, `bt_conn.wts`, `low_power.wts`, `anc_on.wts` och `anc_off.wts`.
- `.wts` är JieLis WTGv2/SILK-baserade ljudformat. JieLis officiella Windowsverktyg kan avkoda filerna till WAV via Wine.

Inget verktyg i detta repo skriver till headsetet. OTA-flashning och modifierad ompackning är medvetet inte implementerade ännu.

Läs headsetets installerade produkt-firmware med UGREENs enda tillåtna
`GET_VERSION`-kommando:

```bash
./tools/read_ugreen_version.py --query
```

Läs JieLi-kretsens transport- och OTA-egenskaper separat:

```bash
./tools/read_device_info.py --query
```

Versionsfältet från det senare kommandot är JieLi-SDK:ns generiska målversion och
ska inte förväxlas med UGREENs produkt-firmware. Utan `--query` gör båda
verktygen en dry-run och skickar ingenting. Resultat från riktiga frågor sparas
lokalt under `artifacts/captures/` och ignoreras av Git.

## Kör analysen

Hämta senaste firmware direkt från UGREEN och verifiera storlek och MD5:

```bash
./tools/fetch_official_firmware.sh
```

Packa upp den lokalt med den pinnade versionen av `jl-misctools`:

```bash
./tools/unpack_firmware.sh
```

Avkoda alla extraherade WTS-prompter till WAV:

```bash
./tools/decode_wts.sh
```

Resultaten hamnar under `artifacts/` och ignoreras av Git. Se [analysrapporten](reports/initial-firmware-analysis-2026-09-03.md) för hashvärden, filinventering och nästa säkra steg.

## Provröster

Skapa tre lokala versioner av Christian Grosshandlares Bluetooth-anslutningsfras
via EutherLink/VoxCPM2:

```bash
./tools/generate_voice_previews.py
```

Verktyget använder den helt syntetiska Christian-referensen från EutherVox och
skapar både käll-WAV och headsetanpassad 16 kHz stereo-WAV under
`artifacts/previews/`. Det packar inte firmware och ansluter aldrig till
headsetet.

Rendera den valda, irriterade Christian Grosshandlare-röstbanken med samtliga
20 prompter:

```bash
./tools/generate_voice_bank.py
```

Repliker och reproducerbara seeds finns i
`voice-banks/christian-grosshandlare-irriterad.json`.

Koda den renderade banken till JieLi WTS vid 12 kbit/s och avkoda varje fil som
roundtrip-kontroll:

```bash
./tools/encode_voice_bank_wts.sh
```

Verifiera att JLFS-röstcontainern kan byggas om byte-identiskt:

```bash
./tools/repack_tone_library.py \
  artifacts/extracted/studio-pro-v0.2.9/files/tone_en \
  artifacts/build/roundtrip/tone_en \
  --require-identical
```

Verktyget kan därefter få en katalog med WTS-ersättningar via
`--replacements`. Utdata ligger under `artifacts/build/` och ignoreras av Git.

## Säkerhetsgräns

Den hämtade V0.2.9-filen är en officiell referensbild, **inte en verifierad backup av den version som sitter i just vårt headset**. Innan en framtida modifiering får flashas måste vi:

1. läsa ut installerad versionssträng via det dokumenterade RCSP/SPP-protokollet;
2. kunna bygga ett paket med korrekta JLFS-, firmware- och UFW-kontrollsummor;
3. verifiera paketet utan hårdvara;
4. ha en testad återställningsväg och exakt originalversion sparad.
