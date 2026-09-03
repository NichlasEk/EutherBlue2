# Linocell BTH13 – passiv JieLi-transportkartläggning

Datum: 2026-09-03

Profilstatus: `research`

## Säkerhetsgräns

Provet fick starta och avsluta vanliga Bluetooth-anslutningar samt läsa
annonserade tjänster och attribut. Inga RCSP-, OTA- eller andra
applikationspaket skickades till lurarna. Ingen firmwarefil valdes eller
överfördes.

## Officiella JieLi-signaturer

JieLis officiella Android-SDK version 4.2.0 innehåller följande standardvärden:

```text
BLE service:             0000ae00-0000-1000-8000-00805f9b34fb
BLE write:               0000ae01-0000-1000-8000-00805f9b34fb
BLE notify:              0000ae02-0000-1000-8000-00805f9b34fb
Classic SPP:             00001101-0000-1000-8000-00805f9b34fb
JieLi GATT over BR/EDR:  0000ae00-0000-1000-8000-00805f9b34fc
```

Värdena lästes ur `BluetoothConstant` i den officiella
`jl_bluetooth_rcsp_V4.2.0_40250-release.aar`. SDK:n beskriver uttryckligen BLE,
SPP och GATT-over-BR/EDR som separata RCSP-transporter.

Referensen var pinnad till Android-JL-Bluetooth-commit
`6293873b641ffd8d461773873ecedef1a9d9038d`; AAR-filens SHA-256 var:

```text
2cb0584ca48491862e03d802aa0b853cc9147cc7e69f84c2e9a55ed1b815ce11
```

Android-JL-OTA lästes vid commit
`4bf054e1ae6e549b617e266cea733576c80c55d5`.

Källa:

- [JieLi – Android JL Bluetooth](https://github.com/Jieli-Tech/Android-JL_Bluetooth)
- [JieLi – Android JL OTA](https://github.com/Jieli-Tech/Android-JL_OTA)

## Resultat i normalläge

En 15 sekunder lång LE-skanning med BTH13 frånkopplad gav ingen BLE-annons från
lurarna. Skanningen startade och stoppade korrekt på datorns adapter.

Efter en vanlig BR/EDR-anslutning blev BlueZ tjänsteupplösning klar, men
GATT-trädet innehöll inga tjänster eller attribut. De enda annonserade
profilerna var A2DP, AVRCP, HFP och PnP som redan finns i huvudrapporten.

Två profilbegränsade anslutningsförsök gjordes utan nyttolast:

```text
0000ae00-0000-1000-8000-00805f9b34fc: ProfileUnavailable
00001101-0000-1000-8000-00805f9b34fb: ProfileUnavailable
```

BTH13 exponerar alltså varken JieLis standard-SPP eller standardprofil för
GATT-over-BR/EDR i sitt vanliga driftläge. Den tidigare datatypen `0xfe` är
annonsmetadata och ska inte sammanblandas med SPP-UUID `fe01`.

## Tolkning

JieLi-chipet är bekräftat via HCI, men RCSP/OTA verkar vara bortbyggt, avstängt
eller endast tillgängligt i ett separat uppgraderingsläge. Frånvaron i
normalläge bevisar inte vilket av dessa tre fall som gäller.

Nästa säkra prov är en ren LE-skanning under det dokumenterade sextrycks-reset-
och omstartsfönstret. Om ingen separat annons eller `AE00`-tjänst syns där
heller krävs antingen en produktspecifik app/firmwarekälla eller fysisk
chip-/flashidentifiering innan någon firmwareväg kan fastställas.
