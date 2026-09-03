# Fysiskt OTA-försök med Christian-firmware

Datum: 2026-09-03

Enhet: UGREEN Studio Pro / HP206 (`00:00:00:00:00:00`)

## Resultat

Den första modifierade Christian-filen överfördes fullständigt men avvisades av
headsetets slutliga dataverifiering. Den modifierade banken aktiverades inte.

| Kontroll | Resultat |
|---|---|
| Fil | `HP206_UGREEN_Studio_Pro_V0.2.9_Christian-UNTESTED-NOT-FOR-FLASH.ufw` |
| Storlek | 2 181 056 byte |
| SHA-256 i appens privata OTA-mapp | `871bb1506489c36beb8d6143ed3c0528f9674c7ed660ddaf6c5356ff52d08d3f` |
| Överföring | Nådde 99,9 % |
| `upgradeStep05` | `Result : 1 (0x1)` |
| Fel | `16389 (0x4005): Data verification failure` |
| Omstartskommando skickat | Nej |

Efter avvisningen förblev den tidigare godkända officiella V0.2.9-banken
körande. Android rapporterade Studio Pro som ansluten och aktiv för både A2DP
och HFP. Stock-filen ligger kvar hashverifierad i klienten för återställning.

Nästa firmwareförsök måste först förklara och reparera den integritetskontroll
som stock-filen klarar men den modifierade filen missar. Samma avvisade fil ska
inte flashas igen.

Råloggen läggs inte i Git eftersom målinformationen innehåller en
enhetsspecifik auth-nyckel.
