# Linocell BTH13 – initial skrivskyddad profil

Datum: 2026-09-03

Profilstatus: `research`

Fysisk enhet: ett anslutet par; Bluetooth-adressen lagras inte i Git.

## Identifiering

Androids Bluetooth-tjänst identifierar den aktiva enheten som `Linocell BTH13`.
Kjell & Company säljer modellen som svart artikel `24366` och vit artikel
`24367`. Den officiella manualen är daterad 2024-12-03.

Ett foto av etiketten i det fysiska laddningsetuiet bekräftar att det testade
paret är den vita varianten `24367`. Etiketten innehåller även koden
`IK144383`, men den gav ingen relevant publik korsreferens och ska tills vidare
behandlas som en intern produkt-, inköps- eller batchkod.

Källor:

- [Kjell & Company – Linocell trådlösa in-ear-hörlurar, artikel 24366](https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/tradlosa-horlurar/linocell-tradlosa-in-ear-horlurar-svart-p24366)
- [Officiell manual för artikel 24366 och 24367](https://www.kjell.com/globalassets/mediaassets/908220_24366_24367_manual_en_no_sv_20241203.pdf)
- [EU-försäkran för artikel 24367](https://www.kjell.com/globalassets/mediaassets/889924_24367_doc_en.pdf)

En lokal, Git-ignorerad referenskopia finns i
`artifacts/references/linocell-bth13/manual-2024-12-03.pdf` med SHA-256:

```text
495a15ba9059519b432b7a034b3dbc26fac70a7f2a8c8416b0b803be525f57a6
```

EU-försäkran finns också lokalt som `24367-doc-en.pdf` med SHA-256:

```text
524c029584041772748a02f562666f4cad8b79264537cbc471fa9e96d161e367
```

Försäkran `DoC-24367-23-09-05` anger Kjell & Co Elektronik AB som ansvarig
tillverkare/EU-representant och modellnummer `24367`. Den innehåller inget
OEM-namn, radiocertifierings-ID eller chipset. PDF-titeln nämner Scandsource,
men detta är Kjell-koncernens sourcingbolag och är inte belägg för vem som
tillverkat själva elektroniken.

## Bekräftat från manualen

- Bluetooth 5.3 med uppgiven räckvidd 10 meter.
- Bluetooth-namn `Linocell BTH13`.
- USB-C-porten på fodralet beskrivs endast som laddning, 5 V/0,5 A.
- Batteritid 6 timmar i snäckorna plus 15 timmar från laddningsetuiet.
- IPX4, touchknappar och röstassistentstyrning.
- Fabriksåterställning: ta ut båda snäckorna och tryck snabbt sex gånger på
  bådas multifunktionsknappar samtidigt. Återställningen utfördes senare under
  undersökningen och återbildade det interna TWS-paret korrekt.

## Bekräftat via ADB

Telefon: Pixel 9a, ansluten via USB-debugging. Följande lästes med
`adb shell dumpsys bluetooth_manager` och `adb shell dumpsys audio` utan att
ändra telefonens eller lurarnas inställningar:

- Den aktiva länken är Bluetooth Classic BR/EDR, inte LE Audio.
- A2DP och HFP är anslutna och aktiva.
- Endast standardtjänsterna Audio Sink (`0x110b`), AVRCP Target (`0x110e`) och
  Handsfree (`0x111e`) annonseras.
- Ingen Serial Port Profile (`0x1101`), leverantörsspecifik UUID eller synlig
  GATT-tjänst annonseras.
- Aktiv ljudkodning är SBC, 44 100 Hz, 16 bit, stereo. Telefonen rapporterar
  inga valbara tilläggscodecs för enheten.
- HFP-loggen visar batterirapportering med `+IPHONEACCEV`.
- Telefonen innehåller tre tidigare parade poster med samma produktnamn.
  Användaren bekräftade att de kommer från flera fysiska BTH13-par som ägs,
  inte från adressbyte hos det undersökta paret. Den aktuella posten är
  identifierad, men adresserna publiceras inte.
- Bluetooth HCI-snooploggning var avstängd och ändrades inte.
- Ingen Linocell-app finns installerad. Den befintliga JieLi OTA-appen härrör
  från HP206-arbetet och är inte bevis för att BTH13 använder JieLi.

## Datorparning och radiosignatur

Efter att telefonens Bluetooth stängts av upptäckte datorn den fysiska enheten
som `Linocell BTH13`. Första parningen skedde innan snäckorna hade bildat sitt
interna TWS-par och gav därför bara ljud i ena snäckan. Datorns bondning togs
bort och manualens sextrycks-reset utfördes på båda snäckorna samtidigt. Efter
omstart bildade de ett par och anslöts som en enda värdenhet.

PipeWire exponerade därefter en stereosink med separata vänster- och
högerkanaler. BlueZ rapporterade ansluten och bondad enhet samt 100 procent
batteri vid mättillfället. Bluetooth-adressen lagras inte i Git.

Parningen gav fler skrivskyddade identitetsfält:

```text
PnP modalias:          bluetooth:v05D6p000Ad0240
Manufacturer ID:       0x7262 (29282)
Manufacturer data:     32327878112233445566aabb0000
Custom AD type:        0xfe
Custom AD data:        a262322e332e352d4032303232313231332d2464633961
Decoded build string:  b2.3.5-@20221213-$dc9a
```

Byggsträngen ser ut att innehålla version `2.3.5`, datum `2022-12-13` och ett
kort bygg-ID `dc9a`. Fältens betydelse är ännu inte styrkt av ett SDK och de
lagras därför som fingerprint, inte som bekräftad produkt-firmwareversion.

Samma manufacturer-ID och testmönster förekommer publikt på flera billiga
Bluetooth-ljudenheter. Det är alltså en användbar familjesignatur men ännu inte
bevis för en viss chipmodell. PnP-aliaset räcker inte heller som chipsetbevis.
Jämförelseexempel:

- [TWS88 med samma manufacturerdata och PnP-alias](https://paul.grozav.info/kb/linux/bluetooth)
- [YMIOT-BT med samma manufacturerdata](https://forums.raspberrypi.com/viewtopic.php?t=378494)

## HCI-identitet

En kort, kontrollerad HCI-fångst gjordes på datorn medan lurarna anslöts och
kopplades från utan avsiktlig ljuduppspelning. BlueZ återanvände först cachad
information, så värden frågade därefter uttryckligen med det skrivskyddade
standardkommandot `Read Remote Version Information` (`0x041d`). Lurarna svarade:

```text
Status:              success (0x00)
LMP version:         0x0c (Bluetooth Core 5.3)
Manufacturer:        0x05D6 (1494)
LMP subversion:      0x22BB
```

Bluetooth SIG:s officiella register tilldelar company ID `0x05D6` till
**Zhuhai Jieli technology Co.,Ltd**. Det bekräftar att BTH13 använder en
JieLi-kontroller och styrker att PnP-vendorvärdet `05D6` verkligen avser JieLi.

- [Bluetooth SIG – Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/)
- [Bluetooth SIG – company ID 0x05D6](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Assigned_Numbers/out/en/Assigned_Numbers.pdf)

Den tidigare annonseringssträngen och publika jämförelser gör AC897-familjen
till en rimlig kandidat. HCI-subversion `0x22BB` identifierar däremot inte en
unik chipmodell, så exempelvis `AC897N` är fortfarande en hypotes och inte ett
fastställt artikelnummer. JieLis officiella OTA-SDK listar AC897 bland stödda
familjer och visar att en möjlig framtida uppgraderingsväg är RCSP över BLE
eller GATT-over-BR/EDR, men endast om produktens firmware faktiskt aktiverat
den tjänsten.

- [JieLi – iOS JL OTA, stödda familjer och transportkrav](https://github.com/Jieli-Tech/iOS-JL_OTA/blob/master/README_EN.md)

En separat passiv transportkartläggning jämförde dessutom lurarna med JieLis
officiella standard-UUID:er. Varken BLE-annons, GATT-attribut, SPP eller JieLis
GATT-over-BR/EDR-profil var tillgänglig i normalläge:

- [Passiv JieLi-transportkartläggning](linocell-bth13-jieli-transport-probe-2026-09-03.md)

## USB-prov

Båda snäckorna placerades i laddningsetuiet och etuiet anslöts i normalt läge
till samma fungerande USB-kabel och datorport som nyss hade burit ADB-trafik
från Pixel-telefonen. Kärnloggen registrerade att telefonen kopplades bort
2026-09-03 14:17:40, men registrerade ingen ny USB-enhet efteråt.

Kontroller med `lsusb`, USB-topologin i sysfs och en sökning efter `ttyACM`,
`ttyUSB`, `hidraw` samt DFU visade ingen enhet som kunde höra till fodralet.
Fodralet enumererar därför inte som USB-enhet i normalt läge. Resultatet stöder
manualens beskrivning av porten som en ren laddningsport. Ett odokumenterat
fabriksläge kan inte uteslutas enbart av detta prov.

## Slutsats

Chipplattformen är nu bekräftad som JieLi, men det finns ännu ingen synlig
firmware- eller styrtransport. Standardprofilerna
kan bära musik, samtal, mediaknappar och batteri men ger ingen generell metod
att läsa firmware eller ersätta interna röstprompter. Det är sannolikt att
prompterna ligger i huvudkretsens interna flash, men exakt SoC, flashlayout och
firmwareformat är ännu okända.

Profilen får därför inte använda HP206:s JieLi-byggdrivrutin oförändrad och får
inte gå vidare från `research` förrän exakt målvariant och en verklig,
återställningsbar firmwareväg har identifierats.

## Nästa säkra undersökningssteg

1. Prova en passiv BLE/RCSP-upptäckt medan lurarna är i normalläge och därefter
   i det dokumenterade resetläget; försök inte starta OTA eller skriva data.
2. Jämför JieLis publika AC897/RCSP-signaturer med den annonserade byggsträngen
   för att snäva in SDK-generationen utan att anta exakt SoC.
3. Fotografera all text på kartong och eventuella regulatoriska etiketter;
   OEM- eller certifieringsnummer kan avslöja exakt chipvariant.
4. Öppna eller löd inte i snäckorna innan modellmärkning och externa
   firmwarekällor är uttömda; de små Li-po-cellerna gör fysisk åtkomst mer
   riskfylld än på ett over-ear-headset.
