# Modellprofiler

Varje headsetmodell får en egen katalog med `profile.json`. Profilen beskriver
det som måste vara sant för just hårdvaran: transport, chipfamilj, stockfil,
firmwarebanker, röstcontainer, kontrollsummelayout, byggdrivrutin och
återställningsläge. Röstrepliker och ljud ligger fortsatt utanför profilen så
att samma röstbank kan återanvändas på flera kompatibla modeller.

## Statusgrindar

- `research`: endast inventering och skrivskyddad analys är tillåten.
- `buildable`: stock-roundtrip, röstformat och samtliga integritetslager är
  verifierade lokalt.
- `working`: en exakt firmware-hash har installerats och fungerat på fysisk
  hårdvara.

Status är dokumentation, inte ett sätt att kringgå kontroller. Varje
byggdrivrutin ska fortfarande avbryta vid storleks-, hash-, roundtrip- eller
CRC-avvikelse.

## Lägg till nästa lur

1. Kopiera `template.json` till `profiles/<modell-id>/profile.json`.
2. Inventera modellnummer, Bluetooth-profiler, USB-beteende, app och chip utan
   att skriva till enheten.
3. Spara en officiell eller utläst stockfil under ignorerade `artifacts/` och
   lås storlek samt SHA-256 i profilen.
4. Packa upp skrivskyddat och identifiera röstcontainer, codec, banklayout,
   kryptering och alla nästlade kontrollsummor.
5. Kräv byte-identisk stock-roundtrip innan en modifierad fil byggs.
6. Dokumentera en realistisk stock-återställning innan fysisk test.
7. Sätt `working` och `verifiedSha256` först när exakt det bygget har fungerat
   på luren.

Lägg aldrig app-token, Bluetooth-authnycklar, lösenord eller andra hemligheter
i en profil. `./tools/eutherblue.py check <modell-id>` avvisar sådana fält.

## Kommandon

```bash
./tools/eutherblue.py list
./tools/eutherblue.py show hp206-jl708n
./tools/eutherblue.py check hp206-jl708n --artifacts
./tools/build_profile_firmware.sh hp206-jl708n
```

`--artifacts` kontrollerar även stockfilens och det fysiskt verifierade byggets
hashar. Kommandona ansluter inte till någon lur.
