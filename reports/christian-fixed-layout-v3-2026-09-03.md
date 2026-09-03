# Christian Grosshandlare fixed-layout v3

Datum: 2026-09-03

Mål: UGREEN Studio Pro / HP206

Bas: officiell UGREEN V0.2.9

Status: **statiskt verifierad men avvisad av headsetets slutverifiering**

## Artefakt

Lokal fil:

`artifacts/build/christian-grosshandlare-irriterad/HP206_UGREEN_Studio_Pro_V0.2.9_Christian-FIXED-LAYOUT-v3-UNTESTED.ufw`

| Egenskap | Värde |
|---|---|
| Storlek | 2 181 056 byte |
| SHA-256 | `725ac44de8dcad03b429ca29a98ff2fea649c625dbe546debdee8fd27162c885` |
| Basfirmware SHA-256 | `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6` |
| Modifierad `tone_en` SHA-256 | `3e292b354d22f48a427e9851c41bb757d32d2910e37450a0ad6ed7eb1b29cedd` |
| WTS-filer | 20 vid 8 kbit/s |
| Interna JLFS-poster | 22, samtliga på originaloffset |
| Modifierade firmwarebanker | `flash.bin` och `flash2.bin` |

## Varför v3 skiljer sig från v2

V2 packade om röstbiblioteket sekventiellt. De nya WTS-filerna hade andra
längder och flyttade därför efterföljande poster till nya offsetar. V3 behåller
varje originaloffset och vägrar bygga om en ersättning inte ryms före nästa
originalpost.

JieLis WTS-avkodare visade att en giltig, kortare WTS-ström inte kan fyllas ut
och ändå räknas som en längre WTS-fil: utfyllnaden avkodas som fortsatt data.
V3 behåller därför den riktiga kodade storleken i respektive JLFS-header och
lämnar resten av det fasta utrymmet utanför posten. Tre korta originalplatser
krävde reproducerbar tempokorrigering; faktorerna ligger i
`voice-banks/christian-grosshandlare-irriterad-fixed-layout.tempo`.

## Verifieringar

1. En oförändrad `tone_en`-roundtrip är byte-identisk med originalet.
2. En oförändrad hel-UFW-roundtrip är byte-identisk med UGREEN-filen.
3. Alla 20 WTS-filer har kodats och kontrollavkodats med JieLis pinnade verktyg.
4. Alla 22 interna poster behåller exakt sina ursprungliga offsetar.
5. Ingen ersättningsfil överskrider utrymmet fram till nästa originalpost.
6. Alla interna header- och data-CRC samt yttre `tone_en`-CRC verifieras efter
   bygget.
7. Både `flash.bin` och `flash2.bin` innehåller samma ersättningscontainer och
   har giltiga UFW-post-CRC.
8. En oberoende firmwareuppackare återläser den modifierade `tone_en`
   byte-identiskt ur den färdiga UFW-filen.

Bygget reproduceras med:

```bash
./tools/build_christian_firmware.sh
```

Artefakten ignoreras av Git. Namnet `UNTESTED` behålls eftersom headsetets egen
slutverifiering inte accepterade filen.

## Kvarvarande risk

V1 och v2 avvisades vid 99,9 procent med `0x4005`. Fixed-layout v3 tog bort den
största kvarvarande strukturella skillnaden men avvisades med exakt samma fel.
Det utesluter de interna WTS-offsetarna och slotstorlekarna som ensam orsak.
Den hashverifierade stock-filen finns kvar för återställning, men hård rollback
efter en faktisk bootloop är fortfarande inte bevisad.

## Fysiskt resultat

Telefonen verifierade v3-filens SHA-256 både i `Download` och i appens privata
OTA-katalog. Endast v3-raden valdes, appen hade en aktiv SPP-session till HP206
och rapporterade `Dual Mode` före start.

| Kontroll | Resultat |
|---|---|
| Överföring | Nådde 99,9 procent utan transportfel |
| `upgradeStep04` | Hela begärda dataområdet lästes |
| `upgradeStep05` | `Result : 1 (0x1)` |
| Fel | `16389 (0x4005): Data verification failure` |
| Omstartskommando | Skickades inte |
| Efteråt | Stockbanken fortsatt ansluten och aktiv för A2DP/HFP |

Samma v3-fil ska inte skickas igen. Nästa bygge måste i stället återskapa den
integritetsmetadata som ändras när `tone_en` ändras.
