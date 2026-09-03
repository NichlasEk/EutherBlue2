# Återställningsberedskap före första OTA-testet

Datum: 2026-09-03

Enhet: UGREEN Studio Pro / HP206

Installerad produkt-firmware: V0.2.5

## Slutsats

Den modifierade firmwaren ska **inte flashas ännu**. Vi har en verifierad
officiell V0.2.9-fil och headsetet rapporterar JieLi dubbelbanks-OTA, men två
olika återställningsnivåer återstår att prova:

1. **Mjuk återställning:** headsetet startar och Bluetooth fungerar, varefter
   den orörda UGREEN V0.2.9-filen installeras igen med en verifierad OTA-klient.
2. **Hård återställning:** den nya banken startar inte. Då måste boot-ROM/
   bootloader automatiskt välja den gamla banken, eller så behövs en fysisk
   programmeringsväg. Detta är ännu inte verifierat på HP206.

## Vad som är bevisat

- Den lokala originalfilen
  `HP206_UGREEN_Studio_Pro_V0.2.9.ufw` är 2 181 056 byte och har SHA-256
  `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6`.
- Headsetets skrivskyddade `GetTargetInfo`-svar rapporterar:
  - protokoll `V_2.0`;
  - projekt `jl_sdk_ac697_publish`;
  - `supportsDoubleBackup = true`;
  - `needsBootLoader = false`;
  - SPP receive MTU 272 och communication MTU 540.
- JieLis officiella Android-SDK skiljer uttryckligen mellan single-backup och
  dual-backup. Dokumentationen säger att återanslutningsflödet används för
  single-backup och inte behöver implementeras för dual-backup.
- SDK-koden tillåter `ExitUpdateMode`/avbrott för dubbelbank, medan den vägrar
  avbryta single-flash OTA. Det stöder tolkningen att den aktiva banken lämnas
  körbar under överföringen, men bevisar inte HP206:s boot-time rollback.
- UGREENs publika `check_upgrade`-API returnerar senaste V0.2.9 när klientens
  `versionCode` motsvarar V0.2.5. API:t erbjuder ingen historisk V0.2.5-fil.

Inget av ovanstående skickade ett OTA-kommando eller skrev till headsetet.

## Så etablerar vi återställningsvägen

1. Bygg en minimal klient runt JieLis officiella OTA-SDK med SPP-prioritet,
   autentisering, fast enhetsidentitet och full loggning. Klienten ska som
   standard bara göra preflight och kräva ett separat, tydligt flashbeslut.
2. Ge klienten enbart den hashverifierade originalfilen V0.2.9 och verifiera
   hela anslutnings-/filkontrollen utan att starta uppgraderingsläget.
3. Gör det första skrivtestet med **orörd officiell V0.2.9**, fulladdat headset
   och utan annan Bluetooth-trafik. Det bevisar transporten men uppgraderar
   samtidigt den installerade V0.2.5; därför görs det först efter ett uttryckligt
   beslut att V0.2.5 får offras.
4. Efter omstart: läs tillbaka produktversion, spela upp alla normala signaler,
   testa av/på, laddning, SPP och ljud. Spara komplett OTA-logg.
5. Först därefter kan en modifierad V0.2.9 övervägas. Om den fortfarande kan
   ansluta återställs den direkt med exakt samma klient och originalfil.
6. Ett kontrollerat test av automatisk bank-rollback är ett separat riskmoment.
   Vi simulerar inte strömavbrott under OTA innan mer plattformsspecifik
   bootloaderdokumentation eller fysisk flashåtkomst finns.

## Lokal spärrkontroll

Kör:

```bash
./tools/check_recovery_readiness.py
```

Verktyget läser bara lokala filer och senaste `target-info`-capture. Det saknar
Bluetooth- och OTA-kod och kan därför inte skriva till headsetet. Det returnerar
exitkod 2 och `NOT READY` tills även de fysiskt testade återställningsbevisen
finns. Flaggor och lyckade firmwarebyggen får aldrig automatiskt göra dessa
grindar gröna.

Ett inert Android-kit kan förberedas med:

```bash
./tools/prepare_android_recovery_kit.sh
```

Skriptet hämtar JieLis signerade exempelklient från den pinnade upstream-
committen `4bf054e1ae6e549b617e266cea733576c80c55d5`, verifierar APK:ns SHA-256,
kopierar endast officiell stock-firmware och skriver ett manifest. Det kör
aldrig `adb`, Bluetooth eller OTA. Kitet är referensmotorn för det första
stock-testet; vår striktare, modellspecifika klient återstår att bygga.

## Nuvarande grindar

| Grind | Status |
|---|---|
| Officiell V0.2.9 sparad och hashverifierad | PASS |
| Enhetsidentitet matchar vår capture | PASS |
| Enheten rapporterar dubbelbank | PASS |
| Enheten rapporterar att separat bootloader-handoff inte behövs | PASS |
| Officiell JieLi-klient ansluter och läser målinfo över SPP | PASS |
| Exakt återställningsbild av installerad V0.2.5 sparad | STOP |
| Stock V0.2.9-restoration testad på detta headset | STOP |
| Automatisk hård rollback testad på detta headset | STOP |

Android/SPP-resultatet och den kvarvarande auth-timeouten finns i
[Android-preflightrapporten](android-spp-preflight-2026-09-03.md).

## Källor

- JieLi OTA SDK: <https://github.com/Jieli-Tech/Android-JL_OTA>
- JieLi utvecklingsanteckningar:
  <https://doc.zh-jieli.com/Apps/Android/ota/en-us/master/development/development_desc.html>
- UGREEN firmware-API:
  <https://api3.ugreeniot.com/app/v1/software/version/check_upgrade>
