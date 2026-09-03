# Linocell BTH13 – BR30-referensfirmware och promptbytesvägar

Datum: 2026-09-03

Profilstatus: `research`

## Slutsats

Det finns nu en verklig firmwarebild att reversera för samma troliga
JieLi-plattform som BTH13: community-repot
`AC897N_AD697N_earphone_release_V2.3.2` innehåller JieLis BR30-earphone-SDK,
källkod, byggverktyg och en färdig `update.ufw`. Bilden går att packa upp med
`jl-misctools` och innehåller ett separat `tone`-filsystem med 16 WTS-prompter.

Detta är en mycket stark **format- och plattformsreferens**, men ännu inte en
bevisat kompatibel BTH13-firmware. Den får därför inte flashas till lurarna.
Kortlayout, GPIO, laddlogik, radioinställningar, flashnyckel och produkt-ID kan
skilja även om systemkretsfamiljen är densamma.

Den viktigaste nya upptäckten är att JieLi också har en officiell mekanism för
att byta enbart promptpaketet över Bluetooth. Appen frågar först enheten om
reserverat utrymme och filnamn, kodar 16 kHz mono PCM till WTS, bygger
`tone.cfg` och överför paketet. Detta är den minst destruktiva vägen om BTH13
har funktionen aktiverad. Våra passiva prover har dock inte hittat RCSP över
BLE, SPP eller GATT-over-BR/EDR, så stödet är inte åtkomligt i normalt läge.

## Den hittade referensbilden

Källa:

- repository: [GZHXXY/AC897N_AD697N_earphone_release_V2.3.2](https://github.com/GZHXXY/AC897N_AD697N_earphone_release_V2.3.2)
- analyserad commit: `a55d953c15e4b9133d8b6b1bc95fabddb2922003`
- sökväg: `cpu/br30/tools/earphone/standard/update.ufw`

Kontrollsummor för de färdigbyggda referensfilerna:

| Fil | Storlek | SHA-256 |
|---|---:|---|
| `update.ufw` | 1 147 776 | `2ea569fdd8b0dc0dcb5ec0ca6a9d96ab291752a5e41920f6dd5dd7037a4e3c8b` |
| `jl_isd.bin` | 495 616 | `fedde3d0946975a9cbef52198d4512be2879fca3ed5389631cc3924bc3c896ad` |
| `jl_isd.fw` | 655 840 | `4f2c7f82b2da0765845a3fb4f60d24e193c1b1165657e5f78f46adc73b92d101` |
| `ota.bin` | 155 033 | `2937a9f9b6e6ffe911c21e1ce0cc2405f363ec3a2aa17333ec5f16eb59833236` |
| `br30loader.bin` | 24 576 | `283c45fd8c725eb0222859f65cfe8a3101fb4eb4c9dc6fa955e2debac27984bb` |

UFW-bilden packades upp utan modifiering med
`kagaimiq/jl-misctools` vid commit
`0a5b12db0ef38f3042acffbe2452730a37fd2405`. Uppackaren rapporterar:

- JieLi new-firmware-format och JLFS version 6;
- chipnamn `AD697N` i containerhuvudet;
- flashstorlek `0x0ff000`;
- entry point `0x01e00100`;
- chip key `0xffff`;
- `app.bin` på 456 684 byte;
- separat `tone`-resurs på 22 544 byte.

Repositoryt benämner familjen AC897N/AD697N och placerar båda under `cpu/br30`.
Att containern säger AD697N visar därför plattformen, inte att BTH13 har exakt
samma kapsling eller kretsvariant.

## Röstbanken i referensen

`tone/index.idx` börjar med signaturen `TIDX` och beskriver följande 16
separata filer:

```text
0.wts  1.wts  2.wts  3.wts  4.wts
5.wts  6.wts  7.wts  8.wts  9.wts
bt.wts
bt_conn.wts
bt_dconn.wts
power_off.wts
power_on.wts
ring.wts
```

Det är precis den struktur som behövs för att kunna ersätta exempelvis
`bt_conn.wts` med grosshandlarens ”Den är ansluten för fan, mannen” utan att
ändra ljudstacken eller Bluetooth-koden. Referensen innehåller dessutom
Windowsverktyg för WTG, MP3/AAC och andra promptformat. Den färdigbyggda
earphone-banken använder däremot WTS, så WTG-verktygen ska inte användas som om
formaten vore utbytbara.

## Varför vår Bluetoothväg hittills är stängd

Standardkonfigurationen i referens-SDK:t har:

```c
//#define CONFIG_APP_BT_ENABLE
#define RCSP_ADV_EN 0
#define RCSP_UPDATE_EN 0
#define USER_UART_UPDATE_ENABLE 0
```

Om app-läget aktiveras sätter samma konfiguration i stället RCSP-annons,
RCSP-update och BLE-stöd till 1. Standardbildens avstängda läge stämmer väl med
det vi har observerat hos BTH13: vanlig A2DP/AVRCP/HFP fungerar, men ingen
JieLi-AE00-tjänst, SPP-kanal eller GATT-over-BR/EDR-kanal blir synlig. Detta är
en förklaring, inte ett byte-för-byte-bevis för att BTH13 kör just denna build.

Konfigurationen visar även att seriell update är möjlig i SDK:t men avstängd i
standardbygget. UBOOT-debug använder `PA05`, en möjlig seriell uppgraderingspin
kommenteras som `PB01`, och reset är satt till åtta sekunder på `PB01` med
`LDOIN` som kommenterat alternativ. De värdena får inte överföras till BTH13:s
kort utan verifierad chipmärkning och ledningsmätning.

## JieLis officiella promptbyte

JieLis aktuella iOS-SDK och dess officiella dokumentation innehåller en komplett
promptbyteskedja:

1. `isSupportTipsVoiceReplace` frågar om enheten stöder funktionen.
2. `voicesReplaceGetVoiceInfo` hämtar maximalt antal filer, exakta filnamn,
   offsetar och storleken på det reserverade området.
3. `JLPcmToWts` kodar rå PCM till WTS. Ingången ska vara 16 kHz, mono,
   16-bitars PCM; exemplet använder målbitrate 20 000.
4. `JLVoicePackageManager.makePks` bygger `tone.cfg` utifrån enhetens egna
   begränsningar.
5. `voicesReplacePushDataRequest` överför bara promptpaketet och kan starta om
   enheten när överföringen är klar.

SDK-demot kontrollerar uttryckligen fel som CRC-fel, slut på minne, uteblivet
svar och avbruten överföring. Det är alltså en avsedd resursuppdatering, inte en
rå flashskrivning. Begränsningen är att protokollet bygger på JieLis RCSP och
måste ha byggts in i produktfirmwaren.

Det finns också ett officiellt firmware-editorflöde där `tone`, `tone_en` eller
`tone_zh` kan ersättas i en firmwarefil. Det kräver rätt licensefil och skapar
en ny hel firmwarebild, så det är mindre attraktivt än promptpaketsvägen men
användbart när vi väl har en verifierad BTH13-stockdump.

## Säker nästa väg

1. Behåll den hittade UFW-bilden som analysreferens; flasha den inte.
2. Använd referensens 16 WTS-filer och JieLis officiella PCM-krav för att bygga
   och storlekskontrollera en grosshandlarbank offline.
3. Leta efter ett dolt RCSP-/testboxläge utan skrivning. Om enheten då visar
   AE00/SPP ska första kommandot bara vara stödfrågan för promptbyte.
4. Om inget sådant läge finns återstår fysisk, läs-only dump via verifierade
   testpunkter. Två identiska stockdump-hashar krävs före någon modifiering.
5. Matcha BTH13-dumpens chipnamn, flashnyckel, entry point, `TIDX`-layout och
   promptlista mot referensen. Först därefter kan en BTH13-specifik bild byggas.

## Källor

- [JieLis officiella dokumentation för promptbyte](https://doc.zh-jieli.com/Apps/iOS/jielihome/zh-cn/master/Development/function.html) – PCM-krav, WTS-packning, enhetsfråga och överföringsflöde.
- [JieLis officiella iOS Bluetooth-SDK](https://github.com/Jieli-Tech/iOS-JL_Bluetooth) – headers och fungerande Swift-demo; analyserad vid commit `a5f3deebbd1db8e82a8671fab870feaea540b839`.
- [JieLis firmware-editor för promptbyte](https://doc.zh-jieli.com/Tools/zh-cn/firmware_tools/firmware_edit/tone_edit.html) – byte av `tone` och flerspråkiga tonresurser i en hel firmwarebild.
- [AC897N/AD697N earphone SDK V2.3.2](https://github.com/GZHXXY/AC897N_AD697N_earphone_release_V2.3.2) – communityspegeln med BR30-källkod och färdig referens-UFW.
- [JieLis officiella OTA-SDK](https://github.com/Jieli-Tech/iOS-JL_OTA) – bekräftar AC897/AD697N-stöd och att firmwarestöd för RCSP krävs.

