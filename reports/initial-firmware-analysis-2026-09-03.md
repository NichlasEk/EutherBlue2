# Första firmwareanalysen: UGREEN Studio Pro

Datum: 2026-09-03

Enhet: UGREEN Studio Pro / HP206

Bluetooth-adress: `00:00:00:00:00:00`

## Resultat

UGREENs Androidapp V2.5.0 visar att modellen använder OTA-ID `studio_pro_ota`. Samma publika API-anrop som appen använder gav den officiella senaste firmwaren V0.2.9. Den signerade, kortlivade nedladdningsadressen har inte sparats i Git.

| Fält | Värde |
|---|---|
| Fil | `HP206_UGREEN_Studio_Pro_V0.2.9.ufw` |
| Storlek | 2 181 056 byte |
| MD5 från UGREEN | `b6ceafc8c653b4dff7df2e0f8716142a` |
| Lokal MD5 | `b6ceafc8c653b4dff7df2e0f8716142a` |
| Lokal SHA-256 | `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6` |
| Publicerad | 2026-05-27 07:43:44 |

Den officiella app-APK som användes för analysen var V2.5.0 (versionCode 917), 327 235 177 byte, MD5 `62fc812eb64edd1e066b90305894e728` och SHA-256 `5191d0aa93b973bd876ecb938d50dfa84fd99850db77d6dc3eade553390ba5f1`.

## Installerad version, läst från headsetet

Två typer av avgränsade läsfrågor kördes mot headsetet över Bluetooth Classic SPP:

| Fråga | Skickat per anrop | Verifierat resultat |
|---|---:|---|
| UGREEN UG1 `GET_VERSION` | 8 byte | Produkt-firmware `0.2.5` |
| JieLi RCSP `GetTargetInfo` | 14 byte | SDK-målversion `V_0.0.0.1`, projekt `jl_sdk_ac697_publish` |

UGREEN-svaret var `DD EE FF 01 01 06 00 02 05 00 00 00 61 ED`.
Svarslängden, successflaggan och CRC16/CCITT-FALSE validerades innan
versionsbytesen `00 02 05` tolkades som `0.2.5`. JieLi-fältet är en generisk
SDK-/transportversion och inte headsetets produkt-firmware.

Den installerade versionen är alltså äldre än den officiella referensfilen
V0.2.9. `GET_VERSION` kördes två gånger för att verifiera det färdiga verktygets
hela flöde, så totalt skickades 30 läsbytes under sessionen (14 + 8 + 8). Inga
uppdaterings-, inställnings- eller OTA-kommandon skickades.

## Firmwarestruktur

Uppackning gjordes med `jl-misctools` på commit `0a5b12db0ef38f3042acffbe2452730a37fd2405`.

- UFW-chipnamn: `JL708N`
- PID: `JL708N`
- Flashstorlek i headern: `0x1ff000`
- Filsystemsversion: 22
- Blockjustering: 16
- Chipnyckel ur `isd_config.ini`: `0x8887`
- Applikation: `app.bin`, 857 353 byte
- Engelskt promptbibliotek: `tone_en`, 56 928 byte
- Kinesiskt promptbibliotek: `tone_zh`, 36 496 byte

Uppackaren når en känd begränsning vid en senare `ALIGN_DIR`-post (`JLFS entry header CRC mismatch`), men applikationen och båda kompletta promptbiblioteken extraheras före den punkten.

## Röstprompter

Engelska biblioteket innehåller 20 WTS-filer:

`power_on`, `power_off`, `low_power`, `bt_conn`, `bt_dconn`, `ring`, `game_in`, `game_out`, `tws_conn`, `tws_dconn`, `anc_on`, `anc_off`, `anc_trans`, `adaptive`, `winddet_on`, `winddet_off`, `fit_det_on`, `pairing`, `key_pairing`, `def_tone`.

Det kinesiska biblioteket innehåller 17 WTS-filer. Totalt avkodades 37 filer framgångsrikt till 16-bitars PCM WAV med JieLis officiella `wtgv2_decode.exe` från SDK-commit `fdc018de81629e21e594d677cf05f87d288be0f0`. Avkodarens SHA-256 är `d9388e8eedb7a3b4295d1f524c347e70512412ac54712e1737196f8380ff663b`.

Det betyder att egna röster är tekniskt realistiska. Det återstår dock två separata problem: att koda nya WAV-filer med rätt WTS-parametrar och att bygga om samtliga nästlade JLFS/UFW-kontrollsummor utan att förändra reserverade områden.

## Vad som inte har gjorts

- Headsetet har inte satts i OTA- eller DFU-läge.
- Ingen firmware har flashats.
- V0.2.9 är inte påstådd vara en dump av den installerade versionen.
- Ingen modifierad UFW har skapats ännu.

## Nästa säkra milstolpe

1. Ta fram en reproducerbar WTS-encoderkedja och jämför original → WAV → WTS mot kända prompter.
2. Implementera en packare som uppdaterar varje inre fil-CRC, bibliotekets CRC, firmwarebildens CRC och UFW-containerns CRC.
3. Gör en byte-för-byte roundtrip där en ompackad men oförändrad firmware blir identisk med originalet.
4. Kartlägg och testa återställningsvägen för den installerade V0.2.5 innan någon skrivning övervägs.
5. Först därefter bedöma om ett modifierat paket kan testas, med laddat batteri och verifierad återställningsväg.

## Källor

- UGREEN firmware-API: `https://api3.ugreeniot.com/app/v1/software/version/check_upgrade`
- UGREEN Audio-app: `https://us.ugreen.com/pages/ugreen-app`
- JieLi OTA SDK: `https://github.com/Jieli-Tech/Android-JL_OTA`
- JieLi WTS-verktyg: `https://github.com/Jieli-Tech/fw-AC63_BT_SDK`
- JL firmwareverktyg: `https://github.com/kagaimiq/jl-misctools`
