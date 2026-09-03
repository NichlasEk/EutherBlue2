# Linocell BTH13 – bildanalys och firmwareväg

Datum: 2026-09-03

Profilstatus: `research`

## Slutsats

Ingen offentlig träff hittades för en reverse engineering av just produktnamnet
`Linocell BTH13`, artikel 24366/24367 eller den troliga PCB-koden. Däremot finns
en öppen och praktiskt relevant reverse-engineeringkedja för JieLi-familjen som
lurarna tillhör:

1. JieLis MaskROM har ett USB-downloadläge kallat `UBOOT1.00`.
2. `jl-uboot-tool` har både BR30-definition och en medföljande
   `br30loader.bin`; projektet anger BR30/AC897N som "seems to work".
3. `jl-misctools` kan packa upp JieLis nyare firmwareformat.
4. Formatdokumentationen visar en separat `tone`-katalog med bland annat
   `bt_conn.wtg`, `bt_dconn.wtg`, `low_power` och `power_off`.

Det betyder inte att BTH13 redan är dumpad eller att den kan skrivas säkert.
Det betyder att vi har en trovärdig dump- och analysväg när krets och testpunkter
har identifierats.

## Det som syns på bilderna

Bilderna visar sannolikt varsin spegelvänd L/R-variant av samma kortkonstruktion,
inte fram- och baksida av samma kort. Kortens lödmask skiljer sig (blå respektive
grön), men komponentplacering och märkningar motsvarar varandra.

Den bästa avläsningen av kortmärkningen är:

```text
T29-7A01-V1.5
```

Mittentecknet är oskarpt och `T29-7C01-V1.5` behålls därför som alternativ.
Datum-/lotkoden ser mest ut som `20230916`. Exakta sökningar på båda
märkningarna, med och utan TWS/JieLi/earbud-termer på engelska och kinesiska,
gav ingen relevant offentlig träff den 3 september 2026.

På den fotograferade sidan syns bland annat:

- den stora mörka kopparytan som sannolik kapacitiv touchyta;
- en tvåfärgs status-LED vid ljusledaren;
- mikrofon/akustisk öppning och små analoga stödkomponenter;
- en central guldfärgad fjäder-/kontaktpunkt;
- inga synliga separata stora flash- eller Bluetooth-kretsar.

Den bekräftade JieLi-systemkretsen sitter därför sannolikt på kortets undersida
eller djupare i kapslingen. Bilderna räcker inte för att läsa dess exakta
AC/AD/JL-beteckning eller identifiera USB D+/D-, VBAT och GND med tillräcklig
säkerhet.

## Varför BR30/AC897N fortfarande är en kandidat

HCI-provet identifierade tillverkare `0x05D6` som Zhuhai Jieli och gav
LMP-subversion `0x22BB`. Det bevisar JieLi men inte modellnumret.

JieLis officiella bootloaderprojekt mappar `AC697N/AC897N` till plattformen
`br30`. Det oberoende `jl-uboot-tool` använder samma mappning och innehåller en
24 576 byte stor USB-loader för BR30. Kandidaten är alltså tekniskt rimlig men
förblir obekräftad tills märkningen på huvudkretsen kan fotograferas.

Bluetooth-PnP-värdet `05D6:000A` ska inte användas som modellbevis. Samma tuple
förekommer för flera helt olika billiga JieLi-produkter. Även den tidigare
observerade tillverkardatan `32327878112233445566aabb0000` finns offentligt i
en orelaterad OBD-II-enhet och är därför sannolikt standard-/testdata, inte ett
unikt BTH13-fingeravtryck.

## Den reverserade USB-vägen

UBOOT är inte vanlig USB från laddningsetuiet. JieLi-kretsens Boot ROM måste vid
uppstart få nyckeln `0x16EF` över sina egna USB D+/D--pinnar. En JieLi
USB-updaterdongel genererar signalen och kopplar därefter igenom USB-bussen till
datorn. En BR30-enhet förväntas då identifiera sig som `BR30 UBOOT1.00`, med den
community-dokumenterade USB-identiteten `4c4a:3042`.

Det förklarar varför det tidigare normala USB-C-provet på laddningsetuiet inte
gav någon enumeration: etuiets port är bara en laddväg och är inte nödvändigtvis
elektriskt förbunden med systemkretsens USB-pinnar.

`jl-uboot-tool` kan läsa flash med kommandot:

```text
read <address> <length> <file>
```

Verktyget kan också skriva och radera. De funktionerna får inte användas i vår
första fas. Flashstorleken måste först fastställas från kretsmärkning eller
flash-ID:ets density-byte.

## Röstresurserna

JieLis dokumenterade nyare firmwarelayout innehåller en resursdel med en
`tone`-katalog och `tone.idx`. Exempelstrukturen innehåller bland annat:

```text
tone.idx
bt_conn.wtg
bt_dconn.wtg
low_power.mp3
power_off.mp3
```

`jl-misctools/firmware/fwunpack_newfw.py` kan dekryptera/packa upp delar av det
nyare formatet och `tonecfgmk.py` kan bygga tonindex och tonkatalog. Uppackaren
beskrivs dock uttryckligen som ofullständig, och någon generell byte-identisk
repacker för en godtycklig BR30-dump är inte färdig. En dump kan därför med god
sannolikhet ge oss originalrösterna långt innan vi har en säker modifierad
flashbild.

## Säker arbetsordning

Nästa fysiska milstolpe är en skarp bild av kortets andra sida, inte ett
flashförsök. Innan kortet matas externt eller ansluts till USB ska vi ha:

1. exakt huvudkretsmärkning och flashstorlek;
2. identifierade GND, VBAT, USB D+ och D- mot datablad eller verifierad pinout;
3. batteriet isolerat från bänkmatning/USB på ett kontrollerat sätt;
4. ett dumpverktyg där write/erase är tekniskt spärrade;
5. två oberoende fulla läsningar med identisk SHA-256;
6. en offline-uppackning som hittar en rimlig JLFS-header och tonresurser.

Först därefter är det rimligt att undersöka en ompackad grosshandlarfirmware.

## Källor och reproducerbarhet

Källor kontrollerade 2026-09-03:

- [JieLi fw-Bootloader](https://github.com/Jieli-Tech/fw-Bootloader) – officiell
  mappning av AC697N/AC897N till BR30.
- [kagaimiq/jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool) – dumper,
  BR30-stöd och flashkommandon; läst vid commit
  `adb3f18889e88ac512ce0a3c4d8cc3d3cb30696a`.
- [Så aktiveras JieLi UBOOT](https://github.com/kagaimiq/jl-uboot-tool/blob/main/docs/how-to-enter-uboot.md)
  – reverse-engineerad USB_KEY-signal och dongelflöde.
- [kagaimiq/jl-misctools](https://github.com/kagaimiq/jl-misctools) –
  firmwareuppackare och tonverktyg; läst vid commit
  `0a5b12db0ef38f3042acffbe2452730a37fd2405`.
- [JieLi new firmware format](https://kagaimiq.github.io/jielie/datafmt/newfw/)
  – dokumenterad JLFS-/tonlayout; källrepo läst vid commit
  `1657d25e6e51df6b2c18cd55cfc576c4a6370c63`.
- [Officiell Linocell-manual](https://www.kjell.com/globalassets/mediaassets/908220_24366_24367_manual_en_no_sv_20241203.pdf)
  – gemensam manual för artikel 24366 och 24367.
- [Exempel på återanvänd tillverkardata](https://askubuntu.com/questions/1481880/having-trouble-understanding-bluetooth-connection)
  – communityexempel från en orelaterad OBD-II-enhet.

De tre `kagaimiq`-projekten är community-reverse-engineering, inte verktyg som
JieLi eller Linocell garanterar. De används därför som lovande tekniska
kandidater och inte som bevis på kompatibilitet med den fysiska BTH13-enheten.
