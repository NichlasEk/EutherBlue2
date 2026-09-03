# Christian Grosshandlare boot-CRC v4

Datum: 2026-09-03

Mål: UGREEN Studio Pro / HP206

Status: **installerad, omstartad och hörbart verifierad på HP206**

## Genombrottet efter v3

JieLis uppdateringskod verifierar inte enbart JLFS- och UFW-kontrollsummorna.
Varje flashbank har också en krypterad 32-byte lång boot-info-post vid offset
`0x1000`. Den anger CRC16 över de följande 971 703 byten som faktiskt skrivs
till den inaktiva banken.

I UGREEN-originalet är det lagrade och beräknade värdet `0xe042`. V3 behöll det
gamla värdet trots att `tone_en` ingår i området; den nya datan gav `0xd86e`.
Det matchar exakt felvägen i den officiella uppdaterarens `download_loop.c`:
efter skrivningen läses banken tillbaka, CRC16 beräknas över hela området och
en avvikelse avslutas som `update data verify err`, vilket OTA-klienten visar
som `0x4005`.

V4 räknar nu om detta fält, räknar om boot-info-postens egen header-CRC och gör
samma operation oberoende i `flash.bin` och `flash2.bin`. Byggaren vägrar gå
vidare om stockvärdet inte först kan verifieras eller om bankernas metadata
skiljer sig.

## Artefakt

Installerad fil:

`artifacts/build/christian-grosshandlare-irriterad/HP206_UGREEN_Studio_Pro_V0.2.9_Christian-BOOTCRC-v4-UNTESTED.ufw`

Reproducerbara framtida byggen får namnet:

`artifacts/build/christian-grosshandlare-irriterad/HP206_UGREEN_Studio_Pro_V0.2.9_Christian-BOOTCRC-v4-WORKING.ufw`

| Egenskap | Värde |
|---|---|
| Storlek | 2 181 056 byte |
| SHA-256 | `4e0a8559c2e60f3625821c81d0f2b078043ef79297bff5009f365b4e50968faa` |
| Basfirmware SHA-256 | `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6` |
| Boot-info datalängd | 971 703 byte per bank |
| Original boot-info data-CRC | `0xe042` |
| Ny boot-info data-CRC | `0xd86e` |
| Ny boot-info header-CRC | `0xe187` |

## Verifieringar

1. Originalets krypterade boot-info-header avkodas och dess header-CRC stämmer.
2. Originalets lagrade `0xe042` matchar CRC16 över exakt 971 703 råa bankbyte.
3. V4:s lagrade `0xd86e` matchar det modifierade området byte för byte i båda
   bankerna.
4. V4:s boot-info-header-CRC `0xe187` verifieras i båda bankerna.
5. Alla tidigare fixed-layout-, WTS-, JLFS-, dubbelbanks- och UFW-kontroller
   passerar.
6. En oförändrad hel-UFW-roundtrip förblir byte-identisk med originalet.

## Fysisk verifiering

| Kontroll | Resultat |
|---|---|
| OTA-filens SHA-256 på telefonen | matchade byggartefakten |
| Överföring | 100 procent utan transportfel |
| `upgradeStep05` | `Result : 0 (0x0)` |
| Omstartskommando | skickat och besvarat |
| Klientresultat | `Upgrade is complete` |
| HFP efter omstart | ansluten |
| A2DP efter omstart | ansluten och aktiv |
| Hörbar röstbank | användaren bekräftade “det funkar!” |

Det installerade innehållet och `WORKING`-bygget är byteidentiska och har samma
SHA-256. Det äldre filnamnet `UNTESTED` beskriver enbart namnet vid själva
försöket, inte längre artefaktens status.
