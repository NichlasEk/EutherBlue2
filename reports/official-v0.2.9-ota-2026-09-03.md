# Fysiskt OTA-test med officiell V0.2.9

Datum: 2026-09-03

Enhet: UGREEN Studio Pro / HP206 (`00:00:00:00:00:00`)

## Resultat

Den orörda officiella UGREEN-filen installerades framgångsrikt på det fysiska
headsetet med JieLis Android-klient över Bluetooth Classic SPP.

| Kontroll | Resultat |
|---|---|
| Fil | `HP206_UGREEN_Studio_Pro_V0.2.9.ufw` |
| Storlek | 2 181 056 byte |
| SHA-256 i appens privata OTA-mapp | `41faae11340001e1d7a5013758296b839e4bbe5c3e86dc859ba9d5aa2fc9a1b6` |
| Klient | `com.jieli.otasdk` V1.9.0 (10905) |
| JieLi OTA-SDK | V1.11.0 (11015) |
| Transport | SPP, priority 1 |
| Dubbelbank rapporterad | Ja |
| OTA-statuskontroll | `Result : 0 (0x0)` |
| Appens slutstatus | `Upgrade is complete` |

OTA startade 10:47:43 lokal tid. Firmwareblocken överfördes kontinuerligt till
99,9 %, varefter headsetet godkände uppgraderingsstatusen och tog emot ett
omstartskommando. SPP kopplades ned som väntat under omstarten. Cirka fem
sekunder senare återanslöt HFP och därefter A2DP; Studio Pro blev åter aktiv
ljudenhet. Användaren bekräftade efteråt att uppgraderingen hade gått bra.

Detta bevisar den mjuka återställningsvägen med den sparade officiella
V0.2.9-filen. Det bevisar inte automatisk boot-time rollback om en modifierad
bank inte kan starta, och det återskapar inte den tidigare installerade V0.2.5.

Råloggen läggs inte i Git eftersom målinformationen innehåller en
enhetsspecifik auth-nyckel.
