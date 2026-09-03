# Christian Grosshandlare firmwarebygge

Datum: 2026-09-03

Mål: UGREEN Studio Pro / HP206

Bas: officiell UGREEN V0.2.9

Status: **byggd och statiskt verifierad, aldrig flashad på hårdvara**

## Artefakt

Lokal fil:

`artifacts/build/christian-grosshandlare-irriterad/HP206_UGREEN_Studio_Pro_V0.2.9_Christian-UNTESTED-NOT-FOR-FLASH.ufw`

| Egenskap | Värde |
|---|---|
| Storlek | 2 181 056 byte |
| SHA-256 | `871bb1506489c36beb8d6143ed3c0528f9674c7ed660ddaf6c5356ff52d08d3f` |
| Basfirmware SHA-256 | `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6` |
| Produktversion i basen | V0.2.9 |
| Installerad produktversion före test | V0.2.5 |
| Modifierad region | `tone_en`, 56 928 byte |
| Modifierad `tone_en` SHA-256 | `c295e0732be60a6ac74062f4bf9aab4ff2f6568879fa57d5d5387f174496052a` |
| WTS-filer | 20 vid 12 kbit/s |
| Ledigt i röstregionen | 12 448 byte |

Firmwarefilen och övriga byggartefakter ignoreras av Git. De reproduceras med:

```bash
./tools/build_christian_firmware.sh
```

## Genomförda kontroller

1. Samtliga 20 AI-renderade WAV-filer konverterades med JieLis officiella,
   hashpinnade WTGv2-verktyg.
2. Samtliga 20 WTS-filer avkodades tillbaka framgångsrikt till 16 kHz stereo
   PCM16.
3. En oförändrad `tone_en`-roundtrip blev byte-identisk med originalet:
   `82dcc330e0d77b5de8ad5d690c3e3fe41b783b2db3ed267e7349999dcf8e5d10`.
4. En oförändrad hel-UFW-roundtrip blev byte-identisk med UGREEN-originalet:
   `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6`.
5. Den modifierade UFW:ns huvudheader, krypterade postlista och
   `flash.bin`-CRC validerades efter bygget.
6. Den oberoende uppackaren läste tillbaka `tone_en`; dess SHA-256 var exakt
   samma som den byggda ersättningscontainern.
7. En diffgränskontroll bekräftade att ändrade byte endast finns i
   UFW-kontrollhuvudena och den fasta `tone_en`-regionen.

JieLi-uppackaren når fortfarande den redan dokumenterade begränsningen vid den
senare `ALIGN_DIR`-posten. Den inträffar även på originalbilden och först efter
att både `tone_en` och `tone_zh` har verifierats och extraherats.

## Röstinnehåll

Röstbanken använder den valda irriterade Christian Grosshandlare-rösten. Några
exempel:

- anslutning: “Den är ansluten, för fan, mannen!”
- frånkoppling: “Vem kapade handelsleden nu då?”
- låg batterinivå: “Tomt i kassan! Ladda mig!”
- brusreducering: “Tyst i handelsboden!”
- inkommande samtal: “Telefon! Svara då, för fan!”

Den fullständiga, reproducerbara replikkartan och alla seeds finns i
`voice-banks/christian-grosshandlare-irriterad.json`.

## Varför filen fortfarande heter UNTESTED-NOT-FOR-FLASH

Statiska format- och CRC-kontroller kan inte bevisa att bootloadern accepterar
ett modifierat paket eller att headsetet kan återställas efter strömavbrott,
protokollfel eller inkompatibel V0.2.9-uppgradering. Headsetet kör V0.2.5, så en
flash skulle både uppgradera programvaran och byta röstbank i samma operation.

Innan flashning krävs minst:

1. verifierad metod att återinstallera en officiell, känd firmware;
2. klarlagt om original V0.2.5 kan hämtas eller återställas;
3. fulladdat batteri och stabil Bluetooth-länk;
4. dokumenterad OTA-sekvens med fel- och återanslutningshantering;
5. ett uttryckligt beslut att acceptera brickningsrisken.

Inget byggverktyg i repot innehåller Bluetooth- eller OTA-skrivfunktioner.
