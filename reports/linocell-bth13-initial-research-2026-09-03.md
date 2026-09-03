# Linocell BTH13 – initial skrivskyddad profil

Datum: 2026-09-03

Profilstatus: `research`

Fysisk enhet: ett anslutet par; Bluetooth-adressen lagras inte i Git.

## Identifiering

Androids Bluetooth-tjänst identifierar den aktiva enheten som `Linocell BTH13`.
Kjell & Company säljer modellen som svart artikel `24366` och vit artikel
`24367`. Den officiella manualen är daterad 2024-12-03.

Källor:

- [Kjell & Company – Linocell trådlösa in-ear-hörlurar, artikel 24366](https://www.kjell.com/se/produkter/ljud-bild/horlurar-headset/tradlosa-horlurar/linocell-tradlosa-in-ear-horlurar-svart-p24366)
- [Officiell manual för artikel 24366 och 24367](https://www.kjell.com/globalassets/mediaassets/908220_24366_24367_manual_en_no_sv_20241203.pdf)

En lokal, Git-ignorerad referenskopia finns i
`artifacts/references/linocell-bth13/manual-2024-12-03.pdf` med SHA-256:

```text
495a15ba9059519b432b7a034b3dbc26fac70a7f2a8c8416b0b803be525f57a6
```

## Bekräftat från manualen

- Bluetooth 5.3 med uppgiven räckvidd 10 meter.
- Bluetooth-namn `Linocell BTH13`.
- USB-C-porten på fodralet beskrivs endast som laddning, 5 V/0,5 A.
- Batteritid 6 timmar i snäckorna plus 15 timmar från laddningsetuiet.
- IPX4, touchknappar och röstassistentstyrning.
- Fabriksåterställning: ta ut båda snäckorna och tryck snabbt sex gånger på
  bådas multifunktionsknappar samtidigt. Detta har dokumenterats men inte
  utförts under undersökningen.

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

Det finns ännu ingen synlig firmware- eller styrtransport. Standardprofilerna
kan bära musik, samtal, mediaknappar och batteri men ger ingen generell metod
att läsa firmware eller ersätta interna röstprompter. Det är sannolikt att
prompterna ligger i huvudkretsens interna flash, men chipfamilj och lagring är
ännu okända.

Profilen får därför inte använda HP206:s JieLi-byggdrivrutin och får inte gå
vidare från `research` förrän chipset och en verklig firmwareväg har
identifierats.

## Nästa säkra undersökningssteg

1. Fotografera all text på laddningsetuiets undersida, kartong och eventuella
   regulatoriska etiketter; OEM- eller certifieringsnummer kan avslöja chipset.
2. Om mer radioinformation behövs kan en kort HCI-snoop av en vanlig
   frånkoppling/återanslutning göras senare. Det kräver att diagnostikloggning
   slås på uttryckligen eftersom loggen kan innehålla privat Bluetooth-trafik.
3. Öppna eller löd inte i snäckorna innan modellmärkning och externa
   firmwarekällor är uttömda; de små Li-po-cellerna gör fysisk åtkomst mer
   riskfylld än på ett over-ear-headset.
