# Android SPP recovery-client preflight

Datum: 2026-09-03

## Resultat

JieLis officiella exempelklient kunde ansluta till UGREEN Studio Pro över
Bluetooth Classic SPP och läsa headsetets RCSP-målinformation. Ingen firmware
valdes, inget uppgraderingsläge aktiverades och inga firmwareblock skickades.

## Verifierad miljö

| Del | Verifierat värde |
|---|---|
| Telefon | Google Pixel 9a |
| Android | 17 / API 37 |
| Telefonbatteri vid test | 87 %, USB-laddning aktiv |
| App | `com.jieli.otasdk` V1.9.0 (10905) |
| JieLi OTA-SDK | V1.11.0 (11015) |
| Kommunikation | SPP / priority 1 |
| SPP UUID | `00001101-0000-1000-8000-00805f9b34fb` |
| Måladress | `00:00:00:00:00:00` |
| Målnamn | UGREEN Studio Pro |

APK:n hämtades från JieLis officiella repo, pinnad till commit
`4bf054e1ae6e549b617e266cea733576c80c55d5`. Lokal och installerad källfil
verifierades mot SHA-256
`bdbea4b7e90d42ea1eb5715575f890afe2057ec6b103a00ba5189bd41705edf5`.

Den orörda UGREEN V0.2.9-filen överfördes till
`Download/EutherBlue-Recovery/` på telefonen. Telefonens egen `sha256sum`
bekräftade
`41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6`.

## SPP- och RCSP-bevis

Den sanerade SDK-loggen visade följande ordning:

1. klienten konfigurerades med `priority=1`, device authentication på och utan
   firmware path/data;
2. SPP öppnades mot den parade Studio Pro-enheten;
3. SPP rapporterade anslutning OK;
4. `GetTargetInfo` skickades och besvarades;
5. svaret rapporterade protokoll 2.0, dubbelbanksstöd, ingen separat
   bootloader-handoff och samma Classic/BLE-adress;
6. sessionen kopplades ned kontrollerat medan `isOTA=false`.

Råloggen sparas inte i Git eftersom enhetsresponsen innehåller en auth-nyckel.
Ingen auth-nyckel återges i denna rapport.

## Kvarvarande stoppunkt

Den generiska JieLi-klientens certifieringshandshake gav
`Auth device timeout` (kod 40977). Klienten fortsatte därefter och lyckades
läsa `GetTargetInfo`, men det bevisar inte att den kan genomföra hela OTA:n.

Före ett stock-test måste vi avgöra om HP206 ska använda:

- JieLi-SDK med device certification avstängd, som motsvarar den redan
  fungerande okrypterade RCSP-läsningen; eller
- UGREEN-appens produktspecifika autentiseringsflöde.

Vi ska inte starta OTA bara för att SPP-preflighten blev grön.
