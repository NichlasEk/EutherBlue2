# Christian Grosshandlare firmwarebygge

Datum: 2026-09-03

Mål: UGREEN Studio Pro / HP206

Bas: officiell UGREEN V0.2.9

Status: **dubbelbanksbygge v2 statiskt verifierat, ännu inte sänt till hårdvara**

## Artefakt

Lokal fil:

`artifacts/build/christian-grosshandlare-irriterad/HP206_UGREEN_Studio_Pro_V0.2.9_Christian-DUALBANK-v2-UNTESTED.ufw`

| Egenskap | Värde |
|---|---|
| Storlek | 2 181 056 byte |
| SHA-256 | `dc7c1d529cba32cf2def78e30a058978b7771277184d9ee59b3176aa85e1ede5` |
| Basfirmware SHA-256 | `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6` |
| Produktversion i basen | V0.2.9 |
| Installerad produktversion före test | V0.2.5 |
| Modifierade regioner | `tone_en` i både `flash.bin` och `flash2.bin`, 56 928 byte vardera |
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
5. Den modifierade UFW:ns huvudheader, krypterade postlista samt CRC för både
   `flash.bin` och `flash2.bin` validerades efter bygget.
6. Den oberoende uppackaren läste tillbaka `tone_en`; dess SHA-256 var exakt
   samma som den byggda ersättningscontainern.
7. En diffgränskontroll bekräftade att ändrade byte endast finns i
   UFW-kontrollhuvudena och de två fasta, speglade `tone_en`-regionerna.
8. Båda krypterade röstregionerna är byte-identiska efter patchningen och kan
   oberoende återvinnas till ersättningscontainern med SHA-256
   `c295e0732be60a6ac74062f4bf9aab4ff2f6568879fa57d5d5387f174496052a`.

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

## Varför filen fortfarande heter UNTESTED

Statiska format- och CRC-kontroller kan inte bevisa att bootloadern accepterar
ett modifierat paket. Officiell V0.2.9 har däremot installerats och startat
framgångsrikt på enheten, och klienten har kvar samma hashverifierade stock-fil
för återställning.

Kvarstående risk före fysisk v2-test:

1. hård rollback efter en eventuell bootloop är ännu inte bevisad;
2. original V0.2.5 har inte återfunnits;
3. v2-paketet är ännu inte accepterat av headsetets slutverifiering.

Inget byggverktyg i repot innehåller Bluetooth- eller OTA-skrivfunktioner.
