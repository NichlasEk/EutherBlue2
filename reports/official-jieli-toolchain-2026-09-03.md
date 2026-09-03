# Officiell JieLi-verktygskedja

Datum: 2026-09-03

JieLis officiella dokumentation pekar ut deras paketmanager och separata
post-build-verktyg för Windows och Linux. Följande filer hämtades endast till
lokal cache och checkas inte in i Git:

| Verktyg | Version | SHA-256 |
|---|---:|---|
| Linux post-build tools | 20260728.1 | `f4a458738c5eec32e78377c76b346bcac1cd515b03eda2b7eb11ab183298a858` |
| `ufw_maker` | 1.1.14 | ingår i Linux-paketet ovan |
| `isd_download.exe` | 4.2.72 | `d581cb0e8ef3eefbce1f02f1b02aae637a239d8713e81d1cd5321339fcec7a55` |

AC635N-konfigurationen i JieLis officiella General-Purpose MCU-repo begär
exakt `isddownload` 4.2.72, `ufwmaker` 1.1.14 och `fwadd` 1.0.16. Den lokala
binären för `isd_download.exe` matchade paketkatalogens SHA-256.

`update.a` i samma officiella underlag innehåller LLVM-bitkod. Inspektion av
`download_loop.c.o` visar dubbelbanksuppdaterarens flöde: den läser
`flash.bin`/`flash2.bin`, validerar UFW- och bildhuvuden, skriver vald bank och
jämför CRC16 över den skrivna programkoden med bootinformationen innan den går
vidare över resursposterna. Detta förklarar vad felvägen "update data verify
err" betyder, men bevisar ännu inte vilken senare kontroll HP206 använder för
att avvisa en ändrad `tone_en`.

Inga tokens, lösenord eller enhetsspecifika auth-nycklar lagras i repot.
