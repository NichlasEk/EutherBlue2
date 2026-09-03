# Linocell BTH13 – offline grosshandlarbank mot BR30-referensen

Datum: 2026-09-03

Resultat: `PASS` mot referenslayout, inte testad eller skriven till BTH13

## Resultat

En komplett röstbank med samma 16 promptnamn som den uppackade
AC897N/AD697N-BR30-referensen har genererats med den lokala VoxCPM2-rösten
Christian Grosshandlare. Banken innehåller bland annat:

- `bt_conn.wts`: ”Den är ansluten, för fan, mannen!”
- `bt_dconn.wts`: ”Vem kapade handelsleden nu då?”
- `power_on.wts`: ”Öppna butiken, mannen!”
- `power_off.wts`: ”Stäng lagret. Jag är färdig.”
- siffrorna 0–9 uttryckta som kronor;
- Bluetooth-, ringsignal- och övriga systemprompter.

Alla filer kodades vid 8 000 bit/s och avkodades omedelbart med JieLis
WTS-avkodare. Banken är 17 977 byte mot referensens 21 683 byte. Varje fil
ryms dessutom inom storleken på motsvarande originalfil; kontrollen är alltså
striktare än att bara kontrollera totalsumman.

## Fast layout och integritet

Referensens ursprungliga `tone`-container återbyggdes först utan ersättningar.
Roundtrippen blev byte-identisk:

```text
originalSize:   22544
rebuiltSize:    22544
byteIdentical:  true
entries:        17 (index.idx + 16 WTS)
```

Därefter ersattes samtliga 16 WTS-filer med grosshandlarbanken. Byggaren
bevarade varje offset, fyllde återstående plats med `0xff`, räknade om varje
fils CRC, varje header-CRC och den yttre containerns CRC och läste sedan tillbaka
resultatet med samma strikta parser.

Den färdiga referenscontainern är fortfarande exakt 22 544 byte och lämnar
3 847 byte outnyttjat inom de fasta filplatserna.

| Artefakt | SHA-256 |
|---|---|
| `tone-reference-fit` | `b07c2ea0fde106ed970afd11fa7833b41082ee52199d95c44bbebae46dd95e03` |
| provlyssning, 36,24 s | `3c82b99508e02c8d40e7a569a51bb5285689a53aaa7a59aacf7ec3364f9abbd5` |

Lokala, Git-ignorerade sökvägar:

```text
artifacts/build/christian-grosshandlare-irriterad-bth13/tone-reference-fit
artifacts/build/christian-grosshandlare-irriterad-bth13/wts-reference-fit/
artifacts/previews/christian-grosshandlare-irriterad-bth13/full-bank/
```

## Reproducerbar byggning

```bash
./tools/build_bth13_reference_voice_bank.sh
```

Skriptet genererar ljuden via den lokala TTS-tjänsten, kodar och återavkodar
WTS, validerar namn och slotstorlekar och bygger `tone`-containern om den
ignorerade referenscontainern finns lokalt. Det innehåller ingen kod för
Bluetooth, USB, seriell kommunikation, OTA, erase eller flash.

## Viktig begränsning

Detta bevisar att grosshandlarbanken passar och är strukturellt korrekt i den
offentliga BR30-referensfirmwaren. Det bevisar **inte** att den fysiska BTH13
har samma promptlista, offsetar, flashnyckel eller kortkonfiguration.
`tone-reference-fit` är därför en laboratoriereferens, inte en firmwarefil och
inte något som får skickas till lurarna innan BTH13:s egen layout har lästs ut
eller enheten själv har rapporterat sina gränser via JieLis promptbyteskommando.

