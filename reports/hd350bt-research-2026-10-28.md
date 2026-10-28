# Sennheiser HD 350BT: väg till egna röstprompter

Datum: 2026-10-28. Slutstatus: Christian-röstbanken har fått COMMIT och
COMPLETE från headsetet. Efter begärd av/på-sekvens bekräftade användaren
”funkar ju kanon!”. Alla 13 prompter är byggda; alla händelser har inte
testats individuellt. Se HANDOFF.md för aktuell status, kandidatens SHA256
och exakta lokala fångster.

Avgörande var att slutföra SYNC -> START -> PROCEED -> COMMIT_REQ ->
COMMIT_CFM -> COMPLETE på första USB-gränssnittet (0a12:4007) direkt efter
bankbytet, med ACL-vakten aktiv över reenumereringen. Verktyget
`tools/run_hd350_first_interface_commit.py` automatiserar sekvensen.
Tidigare slutsatser om ett blockerande signaturfel var för starka och
motsägs av denna lyckade commit. Firmware och protokollfångster stannar lokalt.

## Historisk forskningslogg

Följande avsnitt beskriver tidigare delprov, inte slutstatus. Uppgifter om
att ingen bild överförts eller att commit inte går gäller respektive tidpunkt.

## Slutkontroll efter återupptagningsprovet: normalt och städat

Fördröjd slutläsning lyckades efterSDP-kontroll: firmware5.5.0, bootmode0,
uppdateringsnyckel4 frånvarande(status05), servicekey201FFFF001C.
Capture: artifacts/captures/hd350bt-usb/resume-state-final-normal-delayed-20261028.json.
Ingen tillfällig testkontext finns kvar. Ingen fråga/omstart är nu väntande.
Det fysiska återupptagningsbeviset nedan kvarstår, men ingen röstbild har
överförts eller bankväxlats. Nästa steg kräver kartläggning avinaktiv bank,
ROM-kontroller och återställning innanbilddata/bankbyte kanprovas.

## FYSISKT BEVIS: uppdaterarens validerade återupptagningsläge nått utan bilddata

2026-10-28 lyckades det begränsade provet. Capture:
artifacts/captures/hd350bt-usb/resume-state-observe-sdp-20261028.json.
- Version5.5.0 ochbootmode0 verifierades först.
- Registrering4001/12 svarade0012 (status0+eko; verktyget är rättat).
- UpgradeCONNECT0640 gav00.
- SYNC gav140006024555544803: resume2, vårt id45555448, protokoll3.
- START gav020003000666: godkänt.
- IS_CSR_VALID_DONE_REQ gav0b0000, TRANSFER_COMPLETE_IND.
- UpgradeDISCONNECT gav00. Testnyckel4 raderades ochreadback gav05.
- Reset0 accepterades. IngaDATA/START_DATA/TRANSFER_COMPLETE_RES/COMMIT/
  ABORT/ERASE-kommandon skickades. Exakt VM-opcodelista13,01,16 verifierad.

Detta bevisar fysiskt att skrivbar PS-kontext kan styra uppdateraren till
läget efter validering utan en överförd bild. Det bevisar INTE att modifierad
firmware gårattstarta, attROM-validering saknas eller attbankbyte ärsäkert.
Den inaktiva bankens layout/innehåll och återställning ärfortfarande öppna.

Efter städomstart ombads användaren slåpå. Första omedelbara slutläsningen
fickECONNRESET; SDPkontroll bekräftade åter kanal1. Enfördröjd slutläsning
återstår för attbekräfta normalmode/nyckelabsens efteruppstart. Nyckel4 var
redan verifierat borttagen FÖRE reset. Inga nya skrivningar ska göras förslutkontrollen.

Offlineverktyg: audit_hd350_upgrade_resume.py (C-harness förHandleReady och
räknarspärr), build_hd350_offline_voice_candidate.py (bara prompt10utbytt),
probe_hd350_resume_state.py (begränsat hårdvaruprov + cleanup).
Testbildartifacts/build/hd350bt-UNSIGNED-OFFLINE-ONLY är INTE flashklar:
SHA25626db19737f84a97b754d3e0153ca6242fa9f0b1ee5c96816eda159c8e2585a14,
1550500byte, 9block/47filer, bara14464bytesområdet förprompts/10.prm ändrat.
Allaandra byteoriginalidentiska; RSA-PSSkontrollen underkänner bilden somväntat.

## Avslutat prov: normalmode och originalnyckel verifierade

Efter användarens omstart lyckades kontrollen: version5.5.0, bootmode0,
nyckel201FFFF001C, version5.5.0 efterkontroll. Ingen ytterligare skrivning
eller reset behövdes. Capture:
artifacts/captures/hd350bt-usb/service-one-word-restore-after-restart-20261028.json.
Inga användaråtgärder är nu väntande för detta prov.

Verifierat i denna session: native USB-servicekommando10883d leder till
mode2; GAIA0712 kan skriva nyckel201 somett ord00AA med exakt återläsning;
GAIAreset0202/02 accepterades; fysisk av/på återgavmode0 ochoriginalnyckeln.
Ej verifierat: USB-audio trots klassflaggan, godtycklig flashskrivning,
skrivning av prompts eller kringgång av signerad DFU. Ettordsprovet gav
fortsatt tre HID-interface innan omstart; ingen ytterligare USB ur/in
utfördes specifikt under ettordsprovet. Undvik att kalla detta flashunlock.

## LIVE: startläge2 aktiverat och bekräftat

Servicepaketet10883d skickades EN gång viahidraw7 efter lyckad version/
adresskontroll. Capturehidden-usb-audio-enter-20261028.json.
Efterkontroll över Bluetooth lyckades: version5.5.0, bootMode0002,
PS-nyckel201 fortsattFFFF001C. Capturehidden-usb-audio-post-gaia-20261028.json.
Detta är bekräftad ändring av startläge, INTE bekräftad USB-audio/flashåtkomst.
USB visar fortsatt tre HID-interface och inget ALSA-kort. Användaren har
fått begäran USB ur/in UTAN avstängning. Invänta klar och inventera igen.
Ingen GAIA-reset0 har skickats; headsetet är senast bekräftat iMODE2.
Återställning till normalmode0 är förberedd i restore_hd350_normal_boot.py.
Nyckel201:s innehåll efter nativekommandot matchar ursprunglig avläsning.

## Serviceflaggan aktiverar USB-ljud, inte belagd flashåtkomst

Fortsatt offlineanalys följde nyckel201:s RAM-flagga till0x12329c,
vilket matchar strukturen i referensens sinkUsbConfigInit. Funktionen
hämtar USB RO-konfigurationsblock995 (namnet bekräftat i produktens XML).
Vid0x1232b6 läses flaggan, och den villkorliga instruktionenC889 vid
0x1232ba lägger till mask0x03 i USB device_class. Referensens enum ger
0x01=AUDIO_MICROPHONE och0x02=AUDIO_SPEAKER. Samma funktion lägger
separat till HID_DATALINK0x40 genomCAC9, precis som referensens kod.
Detta pekar på ett dolt USB-ljudläge; det är inte en funnen flashskrivare.

Masktolkningen stöds av AND3->C0B1, OR2->C849 och OR64->CAC9 i
objekt/ELF-referensen. RAM-store8FB1 kalibrerades mot AudioConnect:
originalD5160018, alltså r1 till[r6+24]. Motsvarande flaggläsning ligger
vid0x1232b6. BootSetMode-stubben matchar19/22 byte; avvikelserna är
ett relokerat anrop. PsRetrieve-stubben matchar42/56 byte.

Inga enhetskommandon skickades i denna fortsättning. Startläge2 har inte
aktiverats. Återgång och PS-bufferdetaljer är fortfarande inte fastställda;
läsningen begär1 ord medan skrivningen begär2. Spåret får därför inte
beskrivas som flash-/röstupplåsning. Nästa firmwarearbete behöver undersöka
andra servicegrenar eller en separat dokumenterad minnes-/partitionsväg.
Belägg: artifacts/research/hd350bt/source-search/service-boot-branch-550.json,
memory-instruction-calibration.json, referensobjektet audio.o och
apps/libs/usb_device_class/usb_device_class.h i det ignorerade referensträdet.

## PS-nyckel 201 nu läst från headsetet

Efter användarens omstart lyckades den fasta lässekvensen i en session.
Produktversion före/efter5.5.0, BootGetMode0, RETRIEVE_PS_KEY00c9 svar
0000c9ffff001c (status0, nyckel00c9, dataFFFF001C). Ingen beständig
skrivning eller omstart skickades. Capture:
artifacts/captures/hd350bt-usb/gaia-read-service-boot-key-after-restart-20261028.json.
Tidigare väntan på omstart för denna läsning är avslutad. Nyckelns betydelse,
stackdata inför PsStore samt återgång från startläge2 är fortfarande öppna.
Nästa diskriminerande steg är att följa funktionen0x123256 och dess
RAM-flagga till konsumenterna, innan servicekommandot aktiveras.

## Nytt spår: USB-servicegren med PS-nyckel 201 och startläge 2

Offlineanalysen har isolerat grenen vid DFU-offset0x1235ca. Före det
identifierade BootSetMode-anropet ligger samma instruktion2082 som i
referensens BootSetMode(BOOTMODE_CUSTOM=2). PsStore-anropet före omstarten
får nyckel201 (f00240c9) och längd2 ord (2084). Den begränsade formen för
prefixerad konstantladdning verifierades mot32 objekt/ELF-labelpar.
Kommandonummer61 är fortfarande en decoderhypotes, inte fysiskt verifierat.

En andra funktion vid0x123256 läser samma nyckel, jämför mot0xAA och
skriver tillbaka till den. Ett direkt anrop från0x108a2a hittades. Detta
är ett konkret spår till särskilt servicetillstånd; full stacklayout,
skrivvärde, funktion och återgång från startläge2 återstår att avkoda.
Ingen reset eller beständig skrivning har skickats. Inga bevis ännu för
flashskrivning eller kringgång av signaturkontrollen.

Belägg: artifacts/research/hd350bt/source-search/service-boot-branch-550.json
samt load-immediate-calibration.json. Ett rent läsförsök av PS-nyckel201
nekades vid RFCOMM-connect medECONNREFUSED, innan några paket skickades:
artifacts/captures/hd350bt-usb/gaia-read-service-boot-key-20261028.json.
Användaren har nu fått frågan om av/på för detta läsprov. Vid klar: kör
produktversion, BootGetMode och GAIA_RETRIEVE_PS_KEY0710 medpayload00c9
i en enda session. Skriv inte nyckeln och skicka inte startlägeskommandot
innan effekter/återgång har kartlagts.

## Skrivvägar granskade och testade utan dataskrivning

Efter ny användarbekräftad omstart kördes
`tools/probe_hd350_write_command_validation.py` i en enda RFCOMM-session.
Fångst: artifacts/captures/hd350bt-usb/gaia-write-handler-validation-after-restart-20261028.json.

| Prov | Svar | Tolkning |
|---|---|---|
| STORE_PS_KEY0712 med NOLL payloadbyte |05 INVALID_PARAMETER|Kommandot känns igen; ingen nyckel eller data skickad|
| OPEN_FILE0621 mode02, prompts/10.prm |05 INVALID_PARAMETER|Skrivläge avvisas; ingen fil öppnades för skrivning|
| OPEN_STORAGE_PARTITION0611 med NOLL payloadbyte |01 NOT_SUPPORTED|Direkt partitionsöppning stöds inte i denna väg|
| Efterföljande produktversion |5.5.0|Kommunikation kvar|

Viktigt: en nyckel med noll datalängd kan innebära radering; därför skickades
INGEN nyckel alls i STORE_PS_KEY-provet. Detta verifierar validering,
inte en faktisk beständig skrivning eller uppnådd röstskrivbehörighet.

Statisk jämförelse med länkad ADK6.4 ger nu starkare stöd än förut:
- open_file0x15233c:149/160byte; read_file0x1523dc:214/238;
  close_file0x1524ca:89/96.
- gaia_handle_data_transfer_command0x15277e:127/134byte, sex differenser
  inom långa anrop och en annan byte. Referensvarianten saknar
  open_storage_partition och innehåller filREAD plus VM-upgrade.
- store_ps_key0x1528e0:126/138byte; SAMTLIGA differenser inom långa anrop.
  PsStore-anrop matchat till0x168370. Korta anrop från debugdispatch leder
  till denna funktion. Längd<2 avvisas före allokering/PsStore.
- gaia_handle_debug_command0x1529c6:261/276byte.
Underlag: source-search/gaia-read-write-dispatch-550.json och
source-search/gaia-write-handler-call-audit-550.json.

Ytterligare granskat alternativ: QCC har FileCreate/StreamFileSink för en
separat /rwfs/-namnrymd och StreamFilesystemSink för DEVICE_RO_FS, det senare
bakom StreamFilesystemEnable MIB. Detta är inte direkt skrivning till
prompts/10.prm. Referensens röstspelare konstruerar fasta sökvägar
prompts/%d.prm och headers/%d.idx; språkinställningen ändrar index, inte sökväg.
Kandidater för FileCreate0x16a84e, StreamFileSink0x169fb4,
StreamFilesystemSink0x16a014 och StreamFilesystemSource0x169fe4 hittade via
svagare trapankare, men inga direkta korta/långa anrop till dem i skannat
kodområde. FileFind-kontrollen hittade sex anropsplatser, inklusive GAIA.
Indirekta anrop eller felaktiga kandidater är inte uteslutna. Ingen nåbar
USB/Bluetooth-skrivhandler till dessa API:er har belagts.
Underlag: source-search/filesystem-write-traps-550.json.

Korrigering: äldre capturefält retrieveUser0 avsåg faktiskt nyckel0258.
ADK6.4 ps_if.h anger PSKEY_USR0=650=028a. Det tidigare05-svaret får inte
kallas test av USR0. Verktygets etikett är nu retrieveKey0258; originalcapture
är bevarad oförändrad.

Status: faktisk röstfilläsning fungerar; PS-skrivfunktion finns statiskt och
känner igen anrop, men inget giltigt PS-skrivprov gjort. Ingen röstfil,
firmware, kalibrering eller beständig inställning har skrivits i dessa prov.
Vi har ännu inte en väg från PS-konfiguration till egna ljuddata. Nästa
meningsfulla mjukvarusteg kräver en belagd anropsväg till en filskrivare eller
en accepterad uppdateringsbild; upprepa inte samma växlings-/partitionsprov.

## USB-återanslutning efter debughändelsen kontrollerad

Användaren bekräftade USB ur/in med headsetet fortsatt på. Live-inventeringen
visar hub0a12:4010 och HD350BT1377:6012 med samma tre HID-gränssnitt.
Ingen ny USB-debugfunktion eller extra USB-enhet upptäcktes. Bus/device gick
till002/091(hub) och002/092(headset), vilket stöder faktisk återenumerering.
Normaliserad inventering före/efter är identisk. Fångst:
artifacts/captures/hd350bt-usb/usb-debug-after-reconnect-20261028.json.
Provet gav alltså ingen användbar USB-debugåtkomst. Det avgör inte om event-
handlern saknas, tillståndet nekas av säkerhetsinställningar eller förloras vid
återanslutning. Ingen flashdata skickad, inga nya enhetskommandon i kontrollen.
Nästa mjukvaruarbete kräver en ny belagd väg; upprepa inte samma event/replug.
Tidigare instruktioner om att invänta denna återanslutning är nu historik.

## Riktat Enable USB Debug-prov genomfört

Efter ny bekräftad omstart skickades ff010002000a07214109 en gång.
Efterföljande GAIA-produktversion svarade5.5.0. USB-inventering före/efter
var identisk. Ingen explicit exekveringsbekräftelse för debughandlern;
referensens SEND_APPLICATION_MESSAGE skickar ingen ACK vid normal hantering.
Ingen firmwaredata eller PS-store skickades. Fångst:
artifacts/captures/hd350bt-usb/usb-debug-event-20261028.json.
Nästa kontroll är USB-återanslutning utan avsiktlig powercycle av headsetet.

## Fördjupat försök: faktisk GAIA-filläsning och riktad debughändelse

Efter omstart fungerade GAIA OPEN_FILE0621 med mode00 och namnet
`prompts/10.prm`. READ_FILE0624 läste **14464 byte**, byteidentiskt med
original5.5.0. SHA256:
`b95d9449e8975211af1016d97dca1ec79b9814cccba618818ce8d91b4d4baaf3`.
251 sekventiella lässvar inklusive EOF,254 transaktioner totalt.
Fångst: `artifacts/captures/hd350bt-usb/gaia-file-read-after-restart-20261028.json`.
Rekonstruerad fysisk originalfil och manifest:
`artifacts/original/hd350bt/live-gaia-20261028/`.
Detta är EN röstfil från enheten, inte en full flashbackup eller en skrivväg.

CLOSE_FILE0628 svarade0301: status3 INSUFFICIENT_RESOURCES, stream1.
Stängning är därför inte verifierad. Referensens SourceClose efter sista
SourceDrop är en möjlig förklaring, inte en fastställd orsak. RFCOMM nekar
återanslutning tills omstart, även före detta filprov; koppla inte hela
problemet till just filläsningen. Verktyget `read_hd350_gaia_file.py` har
hårda tids-/storleksgränser och försöker alltid stänga en öppnad ström.
Framing återspelad mot254 verkliga transaktioner, fragmenterade i3byte,
med statuskontroll och utan ny hårdvarukontakt.

Efter ytterligare omstart kördes en samlad statusomgång:
- Produktversion5.5.0; API-payload010205; bootmode00.
- Debug NOP0700 lyckades.
- GET_MEMORY_SLOTS0730 lyckades, payload00be042c (referensen beskriver
  två16-bitvärden för allokeringsplatser och PS-utrymme; inte flashstorlek).
- RETRIEVE_PS_KEY0710 för0258 gav05 INVALID_PARAMETER, inte
  NOT_AUTHENTICATED. En tom/ogiltig nyckel är en möjlig förklaring.
Fångst: `gaia-capabilities-after-restart-20261028.json`.
Inga PS-skrivningar eller firmwarekommandon i dessa prov.

ADK6.4-referensens offentliga testnyckel private.pem jämfördes i minnet
med den publika nyckeln extraherad från officiell5.8.0. De skiljer sig;
stocksignaturen verifieras INTE med referensnyckeln. Nyckelmaterial skrevs
inte ut eller sparades. Rapport: `source-search/reference-signing-key-comparison.json`.
Detta utesluter just denna standardnyckel, inte varje tänkbar firmwareväg.

UsbDebugAllow-kandidaten0x16870e saknar även träff från korta anrop efter
kalibrering av7kortanrop mot referenssymboler. Långa anrop har ytterligare
165 matchande kalibreringsexempel från objektens relokeringar och länkade
etiketter. Det är fortfarande inte en full disassembler. Pointer-sökningen
i usb-debug-call-audit-550.json testade bara adresser med80000000-basen;
relativa dispatchpekare utan bas finns också och får inte räknas som uteslutna.

Nytt konkret spår: originalfirmwarens egen config_definition.gz anger
`Enable USB Debug`=0x109. ADK sink_events.h anger motsvarande applikations-
händelse0x4109; main.c hanterar den under ENABLE_ALLOW_USB_DEBUG och
anropar UsbDebugEnableAllow -> UsbDebugAllow(TRUE). Referensen ändrar
bara cachetillstånd till nästa curatorreset, kräver fortfarande challenge-
response och respekterar efuses. Handlerns inkludering i Sennheiser är ännu
inte bevisad; en giltig enum ensam räcker inte.

Förberett riktat prov: `tools/probe_hd350_usb_debug_event.py`, offline
som standard, paketff010002000a07214109 via GAIA SEND_APPLICATION_MESSAGE.
Kontrollerar5.5.0 före, frågar version efter och jämför USB-inventering.
Ingen firmwaredata, reset, PS-store eller unlock-key-write. Resultatet av
ett faktiskt prov ska läggas till separat; förberedelsen är inte aktivering.

## Ytterligare statisk kartläggning av servicefunktionerna

Användaren tillåter fler prov och kan vid behov löda loss ett chip, men
föredrar fortsatt mjukvaruvägen. Inga ytterligare enhetskommandon skickades
i denna undersökning; nästa okända grenar visade tecken på konfigurationsskrivning.

- Kandidat 0x113fe4 matchar `configManagerGetWriteableConfig`: 22/28 byte
  mot länkad ADK-referens, med skillnader i relativa anrop.
- Kandidat 0x11400a matchar början av `configManagerUpdateWriteableConfig`.
  Den automatiska referensgränsen omfattar även efterföljande kod; värdet
  96/138 är därför inte en fristående funktionsmatchning.
- Servicehjälpare 0x119bf8 anropar båda kandidaterna och
  `ByteUtilsMemCpyPackString` (starkare byteankare vid 0x14f078).
- Servicehjälpare 0x11f8fa anropar samma två konfigurationskandidater.
  Dessa grenar behandlas som möjliga skrivningar, inte läsprover.
  Exakta konfigurationsfält och fullständig kommandokoppling är ännu inte bevisade.

Underlag: `artifacts/research/hd350bt/source-search/service-config-writers-550.json`
och `service-last-callees.json`. Detta är statisk analys, inte fysisk
verifiering av grenarnas effekter.

En svagare kandidat för `UsbDebugAllow` hittades vid 0x16870e
(37/50 byte, ett unikt 12-byteankare). Inga direkta långa anrop hittades
vid halvordsskanning av undersökt kodområde. Korta anrop, tail calls och
indirekta vägar är inte uteslutna; det är inte ett bevis på att debug är
omöjligt. Inget debugaktiveringskommando är belagt eller skickat.

Nästa särskiljande hårdvarusteg är fotografier av kortets båda sidor och
läsbara chipmärkningar. Identifiera extern flash, testpunkter och spänning
innan programmerare ansluts eller något löds loss. En fysisk minnesläsning
är ännu inte visad möjlig, och en dump garanterar inte att modifierade
röstdata accepteras. Röstbytet är fortfarande olöst.

## Fortsatt bedömning av faktisk signaturkod och återställningsbehov

Matchning mot den länkade ADK 6.4-referensen gav följande i original 5.5.0:

| Filoffset | Referensfunktion | Matchning på samma relativa offset |
|---|---|---|
| 0x14e57a | HandleFooterState | 50/50 byte |
| 0x14e6e4 | UpgradeFWIFValidateStart | 56/72 byte |
| 0x14e72c | UpgradeFWIFValidateFinish | 126/146 byte |
| 0x14e8d6 | ce_pkcs1_pss_padding_verify | 392/424 byte |

Avkodade långa anrop i ValidateFinish-kandidaten matchar referensens
ImageUpgradeHashFinalise, ByteUtilsMemCpy16 och rsa_decrypt. Ett kort anrop
leder till den starkt matchade PSS-funktionen. Kodsekvensen efter den
kontrollen, inklusive resultathanteringen, är byteidentisk med referensen.
Det stärker slutsatsen att original 5.5.0 faktiskt innehåller verifieringen;
det är inte längre bara en observation om ett generiskt SDK. Däremot har
ingen modifierad bild överförts, så fysisk acceptans/avvisning och alla
möjliga alternativa kodvägar är fortfarande oprövade.

Källan i ADK 6.4 delar upp äldre ValidateFinalize i ValidateStart/Finish.
De nya filerna hämtades för statisk jämförelse. Underlag:
`source-search/validation-candidates-550.json`. En extra offlinegranskning
av sektion 1:s Imag-header sparades i `image-header-audit-550.json`.
Dess 16 avslutande byte matchar inte MD5 av resten av headern; ingen
kontrollsummealgoritm eller fysisk flashlayout har fastställts genom det.

För en möjlig fysisk backupväg söktes FCC-underlagen DMOSEBT4. Tillverkarens
testunderlag omfattar SEBT3/HD350 och SEBT4/HD450, men fotografierna måste
fortfarande knytas till rätt kortvariant. Metadata för Internal Photos
4534545 och 4534546 hittades. Själva PDF-hämtningen nekades med HTTP 403
från provade FCC-/spegeladresser; inga chip har identifierats från bilderna.
Källor: [testunderlag](https://fccid.io/DMOSEBT4/Test-Report/Test-Report-DSS-4534522),
[internfotometadata](https://fccid.io/DMOSEBT4/Internal-Photos/Internal-Photos-1-4534545).

Användaren har fått frågan om möjlighet till fysisk kortinspektion och
flashläsare, eller om arbetet ska begränsas till USB/Bluetooth. En extern
backupväg är ännu bara ett möjligt nästa spår, inte en färdig anvisning att
ansluta spänning eller skriva till flash. Resultatet är fortfarande **inte
ett fungerande röstbyte**. Ingen ytterligare enhetsmutation gjordes här.

## Fysiskt verifierat serviceprotokoll: version och Bluetooth-adress

Efter ACL-ändringen skickades exakt ett report-16-paket med `10 88 1c`
och nollutfyllnad till totalt 32 byte. Headsetet svarade:
`10881c0000000000353530000000000000000000000000000000000000000000`.
Byte 8–10 är ASCII `550`, vilket stämmer med GAIA-produktversionen 5.5.0.
Svaret behåller kommandokoden **0x1c**, inte den tidigare antagna 0x2c.
Den gamla hypotesen får inte användas som svarskrav. Fångst:
`artifacts/captures/hd350bt-usb/service-version-first.json`.

Efter användarens uppmaning att fortsätta provades den andra identifierade
läsgrenen, kommando **0x19**, med samma ramformat. Svar:
`10881900000000000000000000000000000000000000000000000000000000`.
Bytes 3–5 är LAP, byte 6 UAP, bytes 7–8 NAP (adress anonymiserad).
Sammansatt adress blir **00:00:00:00:00:00**, samma som BlueZ visar.
Detta verifierar mer än ett rent eko av förfrågan. Fångst:
`service-address-first.json`. Verktyget har en fast tvåpostig tillåtelselista
(version/address), inga fria opcodes och inga automatiska återförsök.

Offlinegranskning av anrop längre ned i servicefunktionen gav ytterligare
bytebaserade identifieringar. Svars-wrappern 0x123472 anropar målet
0x14b4c2, som matchar UsbDeviceClassSendReport. Funktionen vid 0x12493c
anropar flera referensfunktioner för routat A2DP/HFP-ljud och volym. Målet
0x11ec18 leder till ett starkt matchande PowerChargerEnable (25 överlappande
16-byte-fönster). Detta understryker att serviceprotokollet blandar läsning
med ändrande operationer. Dessa grenar har inte provats på hårdvaran.
Ingen flashläsnings- eller röstskrivningsgren har ännu identifierats.

Underlag för fortsatt statisk analys: `source-search/extra-handler-tail-callees.json`
och `source-search/service-nested-callees.json` under research-katalogen.
Under denna del skickades enbart de två dokumenterade identitetsfrågorna;
ingen firmwarebild, reset, ändring av laddning eller radering av parkopplingar.

## Förberett enpaketsprov: service-version (historik före första svaret)

Fortsatt jämförelse av minnesläsningar mot objektkod gav stöd för att
`7182` läser byte 1 från register 6:s pekare och `b182` byte 2.
Kontrollflödet i servicefunktionen tyder på kontrollbyte 0x88 följt av
kommando. Intervallet 21–28 och den åttapostiga tabellens sista gren
leder till kandidaten GetDeviceIdFullVersion. Utgående gren innehåller
konstanter som tolkas som markör 0x88 och svarskod 0x2c. Detta är en
firmwarehärledd protokollhypotes; inget faktiskt svar har ännu bekräftat den.

`tools/read_hd350_service_version.py` är begränsat till exakt ett 32-byte
HID-outputpaket `10 88 1c` följt av nollor. Det identifierar VID/PID,
interface 0 och exakt deskriptor före öppning, lyssnar högst fem sekunder
och provar inga alternativa opcodes vid uteblivet svar. Det innehåller
inga mode-/reset-/uppdateringskommandon.

USB återanslöts av användaren. hidraw7 identifierades åter som interface 0
men saknar användaråtkomst efter återanslutningen. Första körningen fick
EACCES före sändning (`service-version-permission-check.json`, sent=false).
För det förberedda provet behövs temporär rw-ACL på just denna nod: HID-
läsfrågan måste skickas som output innan svaret kan läsas. Tidigare r-ACL
är både otillräcklig för sändning och borta efter återanslutningen.

## Rapport 16 avkodad; kandidater till kommandotabeller lokaliserade

Ytterligare referensobjekt för sink_gaia, sink_statemanager och sink_dut
hämtades för statisk jämförelse. 101 objekt-/länkade jämförelseposter
extraherades till `adk642-reference/compare-calibration.json`. För den
avgränsade korta formen med register 0–7 och konstant 0–31 finns 47
kontrollfall, alla med samma avkodningsregel och utan avvikelse. Stora
konstanter kan optimeras till andra sekvenser och ingår inte i kontrollen.

Den korta jämförelsens konstant ligger inte i ett sammanhängande bitfält:
bit 4 i konstanten hämtas från instruktionsbit 11. Därför får ordet
0x2c08 inte feltolkas som konstant 32. I USB-dispatch-kandidaten:

- Filoffset 0x123338, 0x2448: jämför register 1 med **1**.
- Filoffset 0x123342, 0x2c08: jämför samma register med **16**.

Tillsammans med referensens report-ID-dispatch och anropsmålen stärker
detta identifieringen av extra funktionen som hantering av rapport 16,
det ID som det fysiska interface 0 annonserar. Andra instruktionsformer,
särskilt prefixade jämförelser, får inte avkodas med denna regel.

I sektion 9:s konstanta data finns tre intilliggande kandidat-hopp-tabeller
vid filoffset 0x170ab8 (10 poster), 0x170ae0 (8 poster) och 0x170b00
(9 poster). Samtliga poster pekar in i funktionens kandidatintervall
0x12354c–0x12385a när pekarnas flaggbit tas bort. Den andra tabellens
index 4 pekar på grenen med lokal Bluetooth-adress och index 7 på grenen
med GetDeviceIdFullVersion. Indexen är **inte** etablerade kommando-ID:
dispatchens intervallkontroller och eventuell subtraktion måste följas
först. Paketlängd och inledande kontrollfält är fortfarande oavkodade.

Reproducerbar kontroll: `tools/decode_hd350_usb_dispatch.py`, pinnad till
originalfilens SHA-256. Resultat: `source-search/usb-dispatch-tables-550.json`.
Detta verktyg är offline och skickar inga paket. Inget sudo behövdes.

## Den extra USB-funktionen: kandidater till servicefunktioner

Fortsatt offlinegranskning av målet 0x12354c i original 5.5.0 fann den
första förväntade epilogsekvensen `f248d84c` vid 0x123856. Detta ger ett
möjligt funktionsintervall, inte en fullständigt verifierad kontrollflödesgraf.
De första 512 byten skannades efter den kalibrerade anropsformen.
Anropsmål jämfördes mot den länkade referensens .text med unika 16-byte-
fönster. Följande är bytebaserade funktionskandidater:

| Anrop från (filoffset) | Mål | Matchande referenssymbol |
|---|---|---|
| 0x123612 | 0x11455c | deviceManagerRemoveAllDevices |
| 0x123676 och flera senare | 0x11bef2 | PioSetLedPin |
| 0x12370e | 0x12000a | sinkDataGetLocalBdAddress |
| 0x12374a | 0x11421a | GetDeviceIdFullVersion |

GetDeviceIdFullVersion har 19 överlappande unika 16-byte-fönster med
sammanhängande placering vid referenssymbolens början; PioSetLedPin har
10, RemoveAllDevices och GetLocalBdAddress vardera 4. Överlappande
fönster är fortfarande inte oberoende bevis. Det finns även svagare
träffar till PsStore och BootSetMode med ett fönster vardera. Dessa får
inte ensamma användas för att godkänna ett enhetskommando.

Fynden talar för service-/testhantering med både informationsläsning och
ändrande operationer. Inget samband med rå flashläsning har hittats.
Report-ID-villkoret, paketkontrollerna och interna kommando-ID är ännu
inte säkert avkodade. I synnerhet kan korta jämförelseinstruktioner inte
tolkas med samma regler som den redan kalibrerade anropsinstruktionen.
Inga gissade rapporter eller kommandon skickades till headsetet.

Underlag: `artifacts/research/hd350bt/source-search/extra-handler-callees.json`.
Referensobjektet hid_upgrade.o hämtades för fortsatt instruktionsjämförelse;
det exekverades inte. Ingen sudo-ändring behövdes.

## Begränsad avkodning av kompakta anrop och kontroll av REA

REA hittades på `~/rea`, remote morluto/rea, version 6.4.0.
`rea providers --json` kördes utan konfigurationsändringar. Ghidra var inte
konfigurerad, standard-Java var 11, Hopper saknades och IDA var inte
konfigurerad. Den befintliga Ghidra 12.1.4-installationen under UT99:s
local/tools har inga Kalimba-träffar i processorernas .ldefs-filer.
REA-resultatet sparades i `source-search/rea-providers.json`. Ingen
nyinstallation eller uppdatering av REA gjordes.

Rekos öppna KalimbaDisassembler läser fasta UInt32-instruktioner och är
inte en direkt decoder för den kompakta kod som observerats här. Istället
matchades relocationposter från två objektfiler mot samma Lc-etiketter
och målsymboler i den länkade referensbilden. 23 relocationposter kunde
paras ihop; 13 motsvarade den undersökta formen av långt kompakt anrop.
En härledd dekoder gav exakt rätt måladress för alla 13. Andra former
dekoderas inte. Underlag: `adk642-reference/call-calibration.json`.

`tools/decode_hd350_compact_calls.py` kräver dessa kontrollfall och den
pinnade SHA-256 för original 5.5.0. Kandidaten vid filoffset 0x12332a
innehåller följande tre träffar:

| Anropsposition (filoffset) | Målets filoffset | Bedömning |
|---|---|---|
| 0x12333c | 0x106f5e | 43/48 inledande byte matchar AhiUsbHostHandleMessage |
| 0x12334a | 0x12354c | ännu oidentifierad funktion |
| 0x123356 | 0x156d0c | 42/48 inledande byte matchar HidUpgradeSetReportHandler |

De två välmatchade målen stärker dispatch-kandidatens identitet. Det
mellersta målet är ett konkret ställe att fortsätta undersöka för extra
hantering. Vi har ännu inte avkodat villkoret som väljer grenen och får
inte kalla det report 16- eller flashhanterare utan mer bevis. Halvords-
skanning kan ge falska träffar utanför kända instruktionsgränser; verktyget
är uttryckligen ingen fullständig disassembler.

Resultat: `source-search/compact-usb-calls-550.json`. Inga nya paket
skickades till headsetet och ingen sudo-åtkomst behövdes.

## Länkad Kalimba-referens gav kodankare i 5.5.0

Den färdiglänkade `sink.elf` från samma ADK 6.4.2.26-träd hämtades för
statisk analys (34 536 140 byte). ELF anger kompakta kodsektioner vid
0x80000000 och konstanta data vid 0x78000000. Funktionerna är kortare än
i de olänkade objektfilerna; exempelvis är handleHidClassRequest 368 byte
mot objektfilens 744 byte. Detta förklarar varför objektjämförelsen var
ett dåligt första ankare; alla formatdetaljer är inte ännu avkodade.

`tools/match_hd350_linked_hid.py` gör en reproducerbar offlinejämförelse
med överlappande byteankare, utan att kalla dessa avkodade instruktioner.
Interna Lc_-etiketter måste uteslutas vid uppskattning av funktionsslut.

| Kandidat i firmware 5.5.0 (filoffset) | Referensfunktion | Belägg |
|---|---|---|
| 0x14aef6 | usbEnumerateHidConsumerTransportControl | 107/138 byte lika på samma offset |
| 0x14b0dc | hidConsumerHandler | kort, liknar även keyboard-wrappern |
| 0x14b0fe | hidKeyboardHandler | kort, liknar även consumer-wrappern |
| 0x14b120 | hidDatalinkHandler | flera 16-byte-ankare på sammanhängande offset |
| 0x14b144 | handleHidClassRequest | 297/368 byte lika; 26 överlappande 16-byte-ankare |
| 0x12332a | usbHostHandleMessage | svag kandidat: 19/38 byte lika och bara två överlappande 8-byte-ankare |

Träffar är inte oberoende bevis när bytefönstren överlappar. Den gemensamma
HID-hanteraren har betydligt starkare stöd än appens dispatch-kandidat.
Den senare har avvikande kod efter den gemensamma inledningen; detta är
en plats att undersöka för tillverkarspecifik hantering, inte bevis för ett
visst report-ID, kommando eller flashåtkomst. Ingen fullständig Kalimba-
disassembler har ännu tagits i bruk. Systemets objdump gav inget användbart
Kalimba-stöd. Den äldre BlueCore5-instruktionsmanualen är inte verifierad
som korrekt för denna kompakta variant.

Resultat: `source-search/linked-hid-candidates-550.json` och
`source-search/linked-fingerprints-550.json` under research-katalogen.
Inga nya headsetkommandon, ändrade rättigheter eller sudo behövdes.

## Sökning efter interface 0-protokoll och jämförelse med ADK 6.4

Sökning i webben och GitHub hittade QCC3034/ADK 6.4.2.26-källträdet
[JASONYANG1/qualcomm-qcc3034-](https://github.com/JASONYANG1/qualcomm-qcc3034-)
och ett separat [BTD700-protokollprojekt](https://github.com/sinchichou/Sennheiser-Dongle-Control).
Relevanta källor och två ELF-objekt hämtades för lokal statisk analys, inte
exekvering. De ligger i `artifacts/research/hd350bt/adk642-reference/` och
`source-search/`, båda under den ignorerade research-katalogen.

Fynd:

- ADK 6.4:s `sink_usb_debug.c` har UsbDebugEnableAllow, som bara anropar
  UsbDebugAllow(TRUE) när ENABLE_ALLOW_USB_DEBUG är kompilerat. Källans
  kommentar beskriver förändringen som temporär till power cycle/reset.
- API-dokumentationen i `usb.h` säger uttryckligen att USB-debug fortfarande
  kräver challenge-response och beror på efusevillkor. Detta säger inget
  om HD350:s faktiska säkringsbitar eller huruvida funktionen finns i bilden.
- ADK 6.4:s standard-HID-deskriptor identifierar inte HD350:s FFA0/rapport16.
  Det finns fortfarande ingen belagd koppling mellan interface 0 och USBDBG.
- BTD700 använder andra HID-rapporter (0x9a, 3, 0x34) och andra usage pages
  (FFA1/FFA2). Dess kommandon överfördes därför inte till HD350.
- De hämtade `usb_device_hid.o` och `sink_usb.o` är ELF32 för CSR Kalimba.
  En begränsad exakt bytejämförelse av deras pm-funktioner med HD350 5.5.0
  gav inga 16-byte-ankare, varken rått eller med 16-/32-bitars byteswap.
  Det utesluter inte gemensam källkod: kompilator, länkning och kodgenerering
  kan skilja. Det räcker inte för att namnge headsetets kommandohanterare.

Inget tillverkarspecifikt läskommando för interface 0 identifierades i denna
sökning. Nästa statiska steg kräver stöd för rätt Kalimba-instruktionsformat
eller en närmare symbol-/byggmatchning; ett slumpmässigt HID-kommando skulle
inte vara ett belagt läsprov. Inga nya paket skickades till headsetet.

Detaljkällor:
[USB-debug-wrapper](https://github.com/JASONYANG1/qualcomm-qcc3034-/blob/master/apps/applications/sink/sink_usb_debug.c),
[USB API](https://github.com/JASONYANG1/qualcomm-qcc3034-/blob/master/apps/fw/src/gen/customer/core/trap_api/usb.h),
[BTD700-protokoll](https://github.com/sinchichou/Sennheiser-Dongle-Control/blob/main/btd700_probe/protocol.py).

## Fysisk Bluetooth-läsning: installerad produktversion 5.5.0

Efter användarens av-/påslagning lyckades ny RFCOMM-anslutning. I samma
session bekräftades produktversion 5.5.0 och därefter skickades
GET_STORAGE_PARTITION_STATUS, vendor 0x000a, kommando 0x0610, parametrar
device 0/partition 7. Svaret `ff010001000a861001` betyder status 0x01,
GAIA_STATUS_NOT_SUPPORTED enligt referensens gaia.h. Inga partitionsdata
returnerades. Detta belägger att den provade frågan avvisas som ej stödd,
inte att partition 7 saknas eller att alla andra transportvägar är stängda.
Fångst: `artifacts/captures/hd350bt-usb/gaia-after-power-cycle.json`.
Provet skickade endast dessa två GET-frågor; ingen firmwareöverföring,
bankväxling eller konfigurationsändring. Omstarten återställde möjligheten
att öppna GAIA, men orsaken till tidigare anslutningsvägran är inte belagd.

Efter parkoppling identifierade BlueZ HD 350BT på **00:00:00:00:00:00**.
Tidigare anteckning 00:00:00:00:00:00 var en felavläsning av bilden och
ska inte användas. Enheten var paired/bonded/connected och annonserade
GAIA SPP UUID a2129ff3-081b-4c45-8afe-469d9c4842eb. SDP-sökning mot just
denna UUID returnerade RFCOMM-kanal 1; kanalnumret gissades inte.

`tools/read_hd350_gaia_version.py` skickade endast produktversionens GET
`ff01000004940280`. Svar `ff0100070494828000000500050000` har status 0
och major/minor/patch **5/5/0**. Fångst: `gaia-product-version.json` under
`artifacts/captures/hd350bt-usb/`. Detta identifierar nu installerad
produktversion, till skillnad från USB-upgradekanalens fält 1/0/1.
Den tidigare sparade officiella 5.5.0-DFU:n är därmed rätt produktversion
som jämförelseunderlag, men är fortfarande ingen fullständig flashbackup.

Ett efterföljande försök att ansluta för GET_STORAGE_PARTITION_STATUS
(kandidat device 0/partition 7, ej belagd motsvarighet till bildsektion 7)
fick ECONNREFUSED vid socket.connect. Ingen partitionsfråga skickades i
det försöket. Fångst: `gaia-partition-status-0-7.json`. Det felet säger
inget om stöd för partitionskommandot.
Ett senare återförsök efter fortsatt BlueZ-kontroll gav samma
ECONNREFUSED före sändning (`gaia-partition-status-delayed.json`, sent=false).
BlueZ visade fortfarande Connected: yes. Orsaken till nekad ny RFCOMM-
anslutning är inte fastställd; inga upprepade anslutningsförsök gjordes.

## Smart Control: produktversion och automatisk aktivering

Den lokalt extraherade `hd350.json` anger en exakt produktversionsfråga:
`Service_SystemReleaseVersion`, GAIA vendor 0x0494, kommando 0x0280,
svar 0x8280 med tre UINT16-fält (major, minor, patch). Appens `bundle.js`
anger GAIA SPP service UUID `a2129ff3-081b-4c45-8afe-469d9c4842eb`.
Ingen RFCOMM-kanal har antagits eller provats. Bluetooth-kontrollern är
påslagen, men HD350-adressen 00:00:00:00:00:00 finns för närvarande inte
i BlueZ enhetslista. Användaren har ombetts koppla ur USB och slå på
headsetet för Bluetooth så att denna läsfråga kan provas.

Appens GAIA-uppdaterare har separata anrop för följande steg:

- `Upgrade_GaiaSync.invoke([4, fwFileUID])` jämför återupptagningspunkt
  med sparat app-tillstånd. Detta är inte en fristående passiv statusfråga.
- `Upgrade_TransferComplete_Trigger.invoke([1,0])` används före omstart.
- `Upgrade_ProceedToCommit.invoke([1,0])` och
  `Upgrade_CommitCfm.invoke([1,r])` används för commit/rollback.
- `Upgrade_Abort.invoke([0])` används i fel-/avbrytningsvägar.

Det stöder referensens uppdelade aktiveringsflöde men bevisar inte
återställning av HD350 efter strömavbrott. Appen skickar själv
aktiveringskommandon i normalt uppdateringsflöde och är därför inte en
avgränsad testvärd för en modifierad bild. Ingen uppdatering har startats.
Appen innehåller också generell kod för separata röstuppdateringar, men
HD350:s modellfil har inga egenskaper för voice/prompt/language. Den
generella koden är inte bevis för stöd på denna modell.

Extraherade modellposter sparas lokalt i
`artifacts/extracted/hd350bt/app-upgrade-audit.json`. GAIA-referensen har
en separat läsfråga GET_STORAGE_PARTITION_STATUS (0x0610), villkorad av
HAVE_PARTITION_FILESYSTEM. Den läser typ, storlek och monteringsstatus,
inte en verifierad bootbanksflagga. Inga partitionsfrågor har skickats.

## Återställningsgränser inför ett eventuellt signaturprov

Fortsatt statisk granskning av CONFIG_HYDRACORE och referensens
`apps/fw/src/gen/customer/core/trap_api/imageupgrade.h` ger följande ordning:

1. SYNC sparar uppdateringstillstånd; detta är redan en beständig ändring.
2. START_DATA initierar mottagning och kan leda till radering av den andra
   firmwarebanken. DATA skriver bildsektioner via ImageUpgradeStreamGetSink.
3. HandleFooterState verifierar signaturen efter mottagning till SQIF.
   Negativt resultat ger UPGRADE_HOST_ERROR_OEM_VALIDATION_FAILED_FOOTER.
4. Efter validering kan ImageUpgradeCopy köras innan värden godkänner
   aktivering. Att avstå COMMIT innebär alltså inte att inget har skrivits.
5. TRANSFER_COMPLETE_RES med action 0 är en del av vägen till
   ImageUpgradeSwapTry, vilket återstartar med den andra banken.
6. ImageUpgradeSwapCommit ändrar bootinformationen för permanent bankbyte.

ImageUpgradeErase beskrivs som radering av den andra banken och förutsätter
att programmet kör från ordinarie bootbank. UpgradeSMAbort kan kalla denna
radering. UpgradeRevertUpgrades är tom i HYDRACORE-referensen, trots en
generisk kommentar om återställning. Ingen av dessa observationer bevisar
headsetets faktiska bankstatus eller automatisk återgång efter strömavbrott.

Ett framtida hårdvaruprov behöver därför först belägga en återställningsväg
för exakt enhet och firmware. En nedladdad original-DFU är inte en fullständig
backup av kalibrering, parkopplingar eller enhetens flash. Identitetsfrågorna
ovan ger inte bankstatus. Ingen SYNC/START_DATA/ABORT eller original-/testbild
har skickats under denna kartläggning.

Praktisk provordning när återställningsvägen är belagd: dokumentera faktisk
produktversion från Smart Control; använd en kompatibel signerad originalbild
som kontroll för samma transport; förbered därefter en separat, lokalt
verifierad negativ testbild med exakt en ändrad röstbyte och oförändrad
signatur. Ett mottagningsprov måste ha en granskad loggande tillståndsmaskin
som aldrig automatiskt skickar aktiverings-/commit-kommandon. Vid oväntat
svar stoppar värden och journalför läget, utan att gissa ABORT eller reset.
Varken originalkontrollen eller ett hårdvaruprov är ännu genomförda.

Källa: [Image-upgrade API i referensen](https://github.com/KunYi/adk63_sink/blob/master/apps/fw/src/gen/customer/core/trap_api/imageupgrade.h).

## Nytt fysiskt resultat: HID upgrade-identitet

`tools/read_hd350_upgrade_identity.py` genomförde en begränsad session på
interface 2. Referenskoden `hid_upgrade.c`, `upgrade_host_if.c`,
`upgrade_host_if_data.c` och `upgrade_sm.c` granskades först: transportanslutning
registrerar svarsmottagaren, VERSION/VARIANT svarar med metadata och
disconnect tar bort transportmottagaren. Ingen SYNC, START, DATA, ABORT,
ERASE eller COMMIT skickades.

| Operation | Faktiskt svar |
|---|---|
| Feature report 3, connect 2 | report 6, status 0 |
| Output report 5, VERSION_REQ 0x19 | VERSION_CFM 0x1a, fält 1 / 0 / 1 |
| Output report 5, VARIANT_REQ 0x1b | VARIANT_CFM 0x1c, åtta nollbyte |
| Feature report 3, disconnect 7 | skickat utan transportfel; protokollets referens vidarebefordrar ingen disconnect-bekräftelse |

Versionsfälten är upgrade major/minor/config. De identifierar inte
produktversionen 5.x. Den tomma variantsträngen identifierar inte chipet.
Fångst: `artifacts/captures/hd350bt-usb/upgrade-identity-first.json`.
Efterkontroll över en separat AHI-session gav NORMAL (1), med lyckad
AHI connect/disconnect. Fångst: `ahi-mode-after-upgrade-identity.json`.
Detta verifierar fungerande identitetsfrågor på uppdateringstransporten,
inte flashläsning, installation eller accepterande av modifierad firmware.

Spåret kom från [BTD 600-verktygets protokollkod](https://github.com/hhh2210/btd600-fw/blob/main/src/btd600_fw/protocol.py),
men dess enhets-ID och paketstorlekar återanvändes inte. HD350:s egen
deskriptor och Qualcomm-referensen styrde provet. Inga nedladdade verktyg
exekverades. Kopior för statisk läsning ligger i den ignorerade
`artifacts/research/hd350bt/btd600-reference/`.

Kvarvarande avgörande fråga är en belagd väg till resurs-/flashåtkomst
eller faktisk signaturpolicy i headsetet. Offlineproven visar att en
ändrad röst bryter originalsignaturen; hårdvarans avvisning av en sådan
bild har inte provats. Den skillnaden får inte försvinna i slutsatsen.

## Interface 0: firmwarekoppling och passivt läsprov

Den fysiska FFA0-deskriptorn hittades byteexakt i samtliga fyra officiella
firmwareversioner. I 5.8.0 ligger den vid filoffset 0x173f54, relativt
sektion 9 vid 0x6d4f8. Matchningarna sparas i
`artifacts/captures/hd350bt-usb/interface0-firmware-matches.json`.
Det knyter deskriptorn till applikationsbilden men identifierar inte
kommandoprotokollet eller bevisar rå debugåtkomst. Referensens vanliga
consumer-HID-deskriptor skiljer sig från denna; AHI-layouten på interface 2
får därför inte återanvändas som antaget protokoll på interface 0.

`tools/listen_hd350_vendor_usb.py` verifierar USB-ID, interface och exakt
deskriptor och lyssnar sedan högst fem sekunder/64 inputrapporter med
O_RDONLY. Det skickar inga ioctl- eller outputkommandon. Första körningen
verifierade identiteten men fick EACCES (13) vid öppning av `/dev/hidraw7`.
Fångst: `interface0-passive-first.json`. Den tidigare ACL-ändringen gäller
hidraw9, inte hidraw7. Ett tomt resultat efter ett framtida lyckat passivt
prov skulle bara betyda att ingen spontan rapport observerades.

Efter användarens ACL-ändring kördes samma verktyg igen. USB-identitet och
deskriptor matchade, O_RDONLY-öppningen lyckades och fem sekunders passiv
lyssning gav noll rapporter. Fångst: `interface0-passive-after-acl.json`.
Inga kommandon skickades. Detta verifierar läsåtkomst men säger inget om
vilka förfrågningar gränssnittet stöder eller om flashåtkomst är möjlig.

Nästa fysiska prov använde `tools/read_hd350_vendor_input.py`: exakt en
HIDIOCGINPUT(32) för den deklarerade inputrapporten 16, med O_RDONLY och
förnyad kontroll av identitet/deskriptor. Headsetets USB-väg avvisade
GET_REPORT med EPIPE (32). Fångst: `interface0-get-input16.json`.
Detta är en standardiserad HID-läsfråga, ingen SET_REPORT eller gissad
tillverkaropcode. Ingen firmwareöverföring eller lägesändring gjordes.
Se [Linux HIDRAW-dokumentation](https://cdn.kernel.org/doc/html/latest/hid/hidraw.html).
Avvisningen visar inte att gränssnittet är låst eller oanvändbart; ett
request/response-protokoll via outputrapporter kan fortfarande finnas.

Ytterligare statisk granskning i sektion 9 av 5.8.0 fann en pekartabell
vid 0x6d530: 0x7806d517 (HID-interfacebeskrivning), längd 9,
0x7806d520 (endpointdata), 0x7806d4f8 (rapportbeskrivning), längd 31,
nollpekare. Layouten liknar referensens konfigurerbara consumer-HID-
struktur. Detta är en layoutinferens, inte identifiering av dess
kommandohanterare. Referensens `usbConfigureHidConsumerTransport` tillåter
ersättning av standarddeskriptorn; det går därför inte att dra slutsatsen
att denna vendorrapport använder standardkommandon för media eller AHI.
Sökning efter protokollnamn i firmwaresträngarna identifierade inte
hanteraren. Inget belagt tillverkarspecifikt läskommando hittades.

## Verifierad AHI-kommunikation över USB

Efter användarens ACL-ändring kunde interface 2 öppnas. Faktisk ACL gav
användaren rw; feature-provet använde ändå O_RDONLY. GET_FEATURE 3 och 4
avvisades med EPIPE (32). Detta var inte ett transportlås: referensens
`usb_device_hid.c` lämnar GET_REPORT med success=false, medan SET_REPORT
levererar inkommande data till applikationen. Den 65-byte rapportbeskrivning
som hårdvaran exponerar matchar dess HID datalink-layout (storlekar och ID).
Rapport 1 går till AHI, rapport 5 och kommandorapporterna till HID upgrade.
**Interface 2 är en belagd AHI-/uppdateringskanal, inte belagd USBDBG.**
Interface 0 (FFA0) är fortfarande oidentifierat.

En enda AHI_VERSION_REQ över HID output report 1 fick AHI_VERSION_CFM med
status 0x86 NOT_CONNECTED. Därefter skapades en tillfällig AHI-session med
CONNECT_REQ; svaren verifierades mot opcode, report-ID och längd:

| Fråga | Fysiskt svar |
|---|---|
| CONNECT_REQ 0x17 | success 0 |
| VERSION_REQ 0x01 | success, version 0.4 |
| MODE_GET_REQ 0x09 | success, NORMAL (1) |
| PRODUCT_ID_GET_REQ 0x1d | success, 0 (ingen användbar modellidentifierare) |
| APP_BUILD_ID_GET_REQ 0x1f | success, 0 (ingen användbar firmwareversion) |
| CONFIG_GET_REQ 0x05, block 612 | REJECTED 0x81, inga data |
| CONFIG_GET_REQ 0x05, block 619 | REJECTED 0x81, inga data |
| DISCONNECT_REQ 0x19 | success 0 |

Två identifieringssessioner avslutades med bekräftad disconnect; endast
den senare frågade efter konfigurationsblock. `ahi_task.c` i referensen
kräver configuration mode även för CONFIG_GET. Därmed stämmer avvisningen
med normalt driftläge; den bevisar inte att blocken saknas. Ingen MODE_SET,
CONFIG_SET, event injection, reset eller firmware-transfer har skickats.
AHI-sessionens connect/disconnect ändrar endast transportens sessionstillstånd
i den granskade referensvägen. Vi har inte utlöst något reboot-behov.

Verktyg: `tools/read_hd350_ahi_info.py`, fast tillåtelselista med ovanstående
frågor. Det använder O_RDWR eftersom även en semantisk läsfråga måste skickas
som HID-output. Det är skilt från det ursprungliga O_RDONLY-featureverktyget.
Fångster: `features-first.json`, `ahi-version-first.json`,
`ahi-info-session.json`, `ahi-info-and-prompt-settings.json` under
`artifacts/captures/hd350bt-usb/`. Featureläsaren sparar nu även per-report-fel.

Referenser:
[USB HID](https://github.com/KunYi/adk63_sink/blob/master/apps/libs/usb_device_class/usb_device_hid.c),
[AHI-dispatch](https://github.com/KunYi/adk63_sink/blob/master/apps/libs/ahi/ahi_host_if.c),
[AHI-läsning och driftlägen](https://github.com/KunYi/adk63_sink/blob/master/apps/libs/ahi/ahi_task.c).

Nästa relevanta gräns är att skilja AHI-konfiguration från rå flashåtkomst.
AHI-kommandoinventeringen visar konfigurationsblock och konfigurationsfil,
inte en godtycklig filuppladdning till `prompts/`. Att gå till config mode
är därför inte i sig en lösning på signerade röster. Granska först det ännu
oidentifierade interface 0 eller en belagd rå debugtransport; anta inte att
USB-enumerering eller fungerande AHI innebär flashläsning/flashskrivning.

## USB/serviceinventering efter signaturanalysen (första provet)

Fysiskt USB-prov 2026-10-28: användaren anslöt HD350BT med datakabel.
Linux identifierade `1377:6012`, produkt HD 350BT, bakom `0a12:4010`.
Usb.ids-texten för den senare säger Mpow, men är inte bevis för att det
är ett annat headset; här är det den upstream-hubb som observerades vid
anslutningen. `bcdDevice=17.49` är USB-versionsträngen, inte verifierad
produktfirmwareversion.

Tre gränssnitt lästes från sysfs och USB-deskriptorerna:

| Interface | Aktuell nod | Rapporter |
|---:|---|---|
| 0 | hidraw7 | vendor usage page FFA0, ID 16, input/output om 31 byte |
| 1 | hidraw8 | generiskt HID-tangentbord |
| 2 | hidraw9 | vendor usage page FF00; output ID 1/5 (65 byte), input ID 2 (65 byte), input ID 6 (13 byte), feature ID 3/4 (3 byte) |

Rapportstorlekar ovan är payload före report-ID. Noder kan ändras vid
omanslutning och får inte återanvändas utan identitetskontroll.
Ingen mass-storage- eller USB-audiointerface annonserades i detta läge.
USB-dataåtkomst är alltså **fysiskt verifierad**, men debug-/flashåtkomst
är ännu inte verifierad. Samtliga deskriptorer ligger lokalt i
`artifacts/captures/hd350bt-usb/`.

`tools/read_hd350_usb_features.py` är förberett för endast HIDIOCGFEATURE
på ID 3 och 4. Det verifierar VID/PID, interface 2 och exakt descriptor,
öppnar O_RDONLY och innehåller inga output-/SET_REPORT-/flashanrop.
Koden är syntaxkontrollerad. Faktisk statusläsning återstår eftersom
hidraw9 ägs av root med 0600 och `sudo -n` kräver lösenord. Användaren
har fått kommandot `sudo setfacl -m u:LOCAL_USER:r /dev/hidraw9` för enbart
läsåtkomst till just den aktuella noden. Ingen permanent udev-regel är skapad.

Källgranskningen fann även GAIA-kommandon för partitionsstatus och
separat partitionsskrivning i Qualcomm-referensen. De är villkorade av
`GAIA_PARTITION_FILESYSTEM`, som inte är satt i referensens standard-
VARIANTS. Det bevisar varken att Sennheiser aktiverat eller avaktiverat
stödet. Inga sådana kommandon har skickats. GET_MOUNTED_PARTITIONS i
applikationsreferensen triggar dessutom ominitiering av partitionsinfo,
så namnet GET räcker inte för att kalla kommandot helt passivt.

Publika TestFlash-headerfiler beskriver USBDBG och transportlås samt
separata upplåsningsanrop. Det är belägg för ett verktygsspår, inte för
att headsetets debugtransport är olåst. Ett verktyg från denna källa har
inte exekverats. DLL-filen PtTransport analyserades endast med strings
och objdump och hålls lokalt under ignorerade artifacts.

Nästa konkreta prov: läs de två feature-rapporterna, tolka dem mot
belagd transportkod och välj därefter en begränsad identifierings-/läsfråga.
Flashprogrammering, transportupplåsning, reset och okända outputrapporter
ingår inte i den förberedda statusläsaren.

## Senaste resultat: signaturen och händelsetabellen verifierade offline

Detta avsnitt ersätter osäkerheten om signaturalgoritm, publik nyckel och
signerade byte i de tidigare undersökningsanteckningarna längre ned.
Fysisk verifiering av uppdaterarens beteende är fortfarande inte gjord.

### Exakt signaturkedja

- RSA-2048, exponent 65537, PSS med SHA-256/MGF1-SHA-256 och 222 byte salt.
- Den publika modulusen finns i sektion 9 av 5.8.0 vid relativ offset
  `0x6f664`, 256 byte, lagrad med byteordningen omvänd inom varje 16-bitarsord.
- Hashunderlaget är den sammanfogade **rådatan** i sektionerna
  `0, 1, 4, 5, 6, 7, 9` i denna ordning. PARTDATA-taggar, längdfält och
  fyra byte typ/nummer ingår inte. APPUHDR5 och APPUPFTR ingår inte heller.
  Resursfilsystemet i sektion 7 ingår däremot helt.
- Exakt samma publika nyckel verifierar alla fyra originalversionernas
  256-byte APPUPFTR-signaturer. Detta är kryptografisk verifiering, inte
  bara igenkänning av ett filformat.
- En enda bit ändrad i första byten av `prompts/10.prm` gör verifieringen
  ogiltig. Negativtestet görs i RAM; inget modifierat firmwarepaket skrivs.
- `tools/verify_hd350_signature.py` återupprepar kontrollen. Den tar nyckeln
  från en separat 5.8.0-originalfil vars SHA-256 är pinnad i verktyget.
  Kandidatfilen får alltså inte definiera sin egen betrodda nyckel.
- Rapport: `artifacts/extracted/hd350bt/signature-verification.json`.

Metoden hittades med hjälp av
[Qualcomm ADK-referensens verifierare](https://github.com/KunYi/adk63_sink/blob/master/apps/libs/upgrade/CONFIG_HYDRACORE/upgrade_fw_if_config.c)
och dess RSA-strukturer. Referensen definierar signing mode 1 som
ALL_PARTITIONS_SIGNING_MODE och verifierar PSS efter hashing av sektioner.
Dess exempelmodulus matchar inte HD350-bilden och användes inte som
betrodd nyckel. I stället hittades en modulus i Sennheisers egen sektion 9
genom Montgomery-konstantens placering och verifierades sedan mot samtliga
fyra riktiga signaturer. Referenskod ligger lokalt under
`artifacts/research/hd350bt/adk63-reference/`.

**Konsekvens:** om headsetets verifierare upprätthåller denna signatur
kan en modifierad röstbank inte installeras med normal ompackning och
nya CRC/MD5. Att ändra appens localOTA-väg löser inte den kontrollen.
En publik verifieringsnyckel kan inte skapa nya giltiga signaturer.
En separat service-/resursväg eller belagd alternativ verifieringsväg
behöver hittas; ingen sådan är etablerad ännu.

### Händelser till prompt-ID

En 96-byte tabell med 16 poster matchar event-layouten från den inbäddade
konfigurationsdefinitionen: tre little-endian UINT16 per post, prompt-ID
i högbyten av tredje ordet. Tabellen finns exakt en gång i sektion 9 i
varje originalversion och är byteidentisk. Offset är `0x6a8d2` i 5.8.0
och 5.6.2, `0x6a646` i 5.5.0, `0x6a5e6` i 5.4.0.

| Prompt-ID | Händelse enligt statisk tabell |
|---:|---|
| 0 | SLC Connected |
| 1 | Link Loss, SLC Disconnected, Reconnect Failed |
| 2 | Reject, Three Way Release All Held |
| 3 | Last Number Redial |
| 4 | Cancel End |
| 5 | Battery Low |
| 6–9 | Gas Gauge 0–3, batterinivåer |
| 10 | Power On |
| 11 | Power Off |
| 12 | Enter Pairing |

Fulla event-ID, maskfält och offsets finns i
`artifacts/extracted/hd350bt/prompt-events.json`.
Detta är statisk koppling, inte en lyssningsbekräftad transkription eller
fysisk kontroll av när varje replik spelas.

### Första lokala ersättningsresursen

`artifacts/build/hd350bt-offline-resource/10.prm` återanvänder Christian-
röstbankens `power_on-16k-stereo.wav`. Provfilen har 14464 byte, exakt
113 SBC-ramar, 16 kHz mono, bitpool 60 och 0.904 sekunders speltid.
Alla ramhuvuden kontrollerades och FFmpeg avkodade filen utan fel till
`10-preview.wav`. Den är **inte installerbar firmware**.

Originalinspelningen var 1.76 sekunder. Provet använder `atempo=2` och
utfyllnad för att behålla exakt originalstorlek. Taltempo/ljudkvalitet har
inte accepterats genom lyssning. En kortare ny replik är lämpligare om
vi behöver behålla denna fasta storlek i ett framtida hårdvarutest.
SHA-256: `a3f1f2261f6114553b27daac10c4d307857641e9fea28309d987c7d7ab308e2c`.

### Nästa diskriminerande steg

Kartlägg om signaturverifieringen i enhetens uppdateringskod har en
separat dokumenterad service-/resursväg. Den normala OTA-filens signatur
är nu utredd; ytterligare CRC-ompackning är inte ett meningsfullt nästa prov.
Undersök USB-/debuggränssnittets faktiska åtkomst och originalåterställning
innan någon fysisk skrivning övervägs. Ingen flashning, återställning,
nedgradering eller omstart har utförts.

## Genombrott med appen från telefonen

Smart Control 4.9.3, versionCode 147651, hämtades med ADB från användarens
Pixel 9a. Base och fyra split-APK ligger lokalt i
`artifacts/original/hd350bt/app/`, med storlek/SHA-256 i `manifest.json`.
Base SHA-256: `0141ef9e8825e66bdcfb3d96c763b65da5940817ba793e7910bb1447deaac4e8`.
Signeringscertifikatet har inte verifierats separat. Appen installerades av
användaren från Play; den hämtade appkoden har inte exekverats på datorn.

`assets/app/hd350.json` säger `protocol: GAIA` och `articleNumber: 300002`.
GET mot `v2/availableSystemReleases/300002?os_type=android` gav
5.8.0, 5.6.2, 5.5.0 och 5.4.0. Respektive
`v2/systemRelease/300002/VERSION?os_type=android` returnerar ett `FW_FULL`.
Alla fyra manifest och krypterade original är bevarade under
`artifacts/original/hd350bt/`.

Appens `decryptPackage()` använder AES-CTR med räknarstart 5, följt av ZIP
och jämförelse mot medföljande MD5. Nyckelmaterial behålls enbart i den
lokala originalappen; det dokumenteras inte här. Alla fyra paket klarade
ZIP-CRC och medföljande MD5. Detta är format-/integritetskontroller, inte
verifiering av firmware-signaturen.

| Version | DFU-byte | SHA-256 för dekrypterad DFU |
|---|---:|---|
| 5.8.0 | 1551152 | `cf4a07ddefc6b7c3225a42c21592f9ccae5fed08b88b7f15b95372526ee99df6` |
| 5.6.2 | 1551148 | `acfad5f003bc588ef49b926954a7846621ecbc5feea7ef3aaa6c5b995f5d3d5b` |
| 5.5.0 | 1550500 | `25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48` |
| 5.4.0 | 1550404 | `33348777bc0fb57d79c1369b6ff77e80438a95daf2b00b8e219f78c325c57cbf` |

5.8.0 krypterat original: 1115595 byte,
SHA-256 `c4686167c23c81df219de2b00c754d46f7165f8467ac513729e6825b6fe83c0d`.

## Firmwarestruktur och ljudformat

`tools/inspect_hd350_firmware.py` är en offline-parser utan Bluetooth,
flashning, ompackning eller signaturändring. Den verifierar blockgränser,
byte-identisk återmontering av originalblock, File-bildens storlek,
namn/data-gränser och katalogträd. Samtliga fyra bilder ger nio block och
47 filer från de två byteadresserade File-bilderna. Andra partitioner
sparas råa och är inte påstått avkodade.

5.8.0 innehåller APPUHDR5 (36 byte), PARTDATA med typ 0 och nummer
0, 1, 4, 5, 6, 7, 9, samt APPUPFTR (256 byte).
PARTDATA 7 innehåller `headers/0.idx`–`12.idx`, `prompts/0.prm`–`12.prm`
och `config_definition.gz`. Hela denna partition är byteidentisk mellan
alla fyra versionerna, SHA-256 inklusive dess fyra identifierarbyte:
`15e199f087e984c19b9dbf52565ff646eab6996db3c9558c68e969cb1f5905ac`.

Samtliga 13 prm-filer är fullständigt genomgångna ram för ram: SBC,
16 kHz, mono, 16 block, 8 subband, bitpool 60, 128 byte per ram, 8 ms
per ram. Alla avkodades utan FFmpeg-fel till 16-bitars PCM-WAV i
`artifacts/previews/hd350bt-stock-5.8.0/`. Layout och längder finns i
`layout.json`; promptlängderna är 0.752–3.120 sekunder. Semantiken
(vilken replik hör till vilket nummer) är ännu inte verifierad genom
lyssning eller eventtabellen. IDX-filerna är extraherade men dess fält
är inte fullständigt tolkade.

APPUHDR5 identifierar familjen som `QCC512Xx`. Firmwarepaketets egen
konfigurationsdefinition anger däremot
`HwVariant="QCC3034-AA_DEV-BRD-R2-AA"`, `SwVariant="Headset-Gaming"`.
Det är ett konkret QCC3034-byggspår, inte fysisk avläsning av kretsen.
QCC512X i paketheadern ska därför inte användas som exakt chipmodell.

## Vad signatur- och appkartläggningen faktiskt visar

- APPUPFTR innehåller 256 icke-noll byte i varje version. Headern slutar
  med värdet 1 som [BTD600-parsern](https://github.com/hhh2210/btd600-fw/blob/main/src/btd600_fw/firmware.py)
  tolkar som signing mode. Formatet talar starkt för signerad OTA.
  Algoritm, publik nyckel, exakt signerad byteföljd och faktisk kontroll
  på detta headset är ännu inte verifierade. Ingen signatur är beräknad
  eller kringgången. 256 byte ensamt bevisar inte RSA-2048.
- Appen innehåller felkoder för signaturlängd (52), OEM-validering (27),
  partitionsdata (60) och footer (61). Det är generisk GAIA-kod, inte
  bevis att alla felvägar används av just HD 350BT.
- Appens generiska `startLocal()`/`localOTA` kan mata en lokal rå DFU
  förbi AES/ZIP/MD5-steget. Det förändrar inte headsetets verifierare och
  bevisar inte att osignerad firmware accepteras. Vägen har inte aktiverats.
- Separat röstpaketstöd finns i appen för andra produkter, men HD350:s
  modell-JSON saknar VoicePrompt_Language och AudioPrompt-överförings-
  kommandona som den vägen kräver. Alla fyra manifest listar bara FW_FULL.
  Ingen fungerande separat röstuppladdningsväg är belagd för HD 350BT.
- Den inbäddade konfigurationsdefinitionen beskriver event→prompt i
  BlockId 625, promptinställningar i 612 och 619, och en GAIA DFU-partition
  i 982. Detta är schemainformation, inte avlästa aktuella värden och inte
  en möjlighet att skriva om själva prm-resurserna.
- Modellspecifik läsfråga för installerad version finns dokumenterad i
  appen: vendor `0x0494`, kommando `0x0280`, svar `0x8280`, tre UINT16
  (major/minor/patch). Den har inte skickats; installerad version är okänd.

## Prioriterat nästa arbete

1. Kartlägg verifieraren för APPUPFTR: hitta publik verifieringsnyckel och
   hash-/signaturkedja i råpartitionerna eller belagd Qualcomm-formatkod.
   Använd fyra original som oberoende kontrollmaterial. Inget muterat
   paket skickas till headsetet som ett sätt att gissa valideringsregler.
2. Avkoda konfigurationspartitionen och BlockId 625 för händelse→prompt.
   Matcha med lyssning på de extraherade WAV-filerna.
3. Pröva offline-encoding till samma SBC-parametrar och exakt antal ramar.
   Börja med en enskild resurs med oförändrad storlek, behåll IDX och layout.
   Detta ger en resurskandidat, inte en installerbar firmware.
4. Om OTA-signering verkligen hindrar modifiering: utred belagd separat
   resursväg/serviceåtkomst eller identifiera hårdvara och läsåtkomst.
   Skrivbar konfiguration ska inte förväxlas med skrivbart resursfilsystem.

Originalfirmware, APK, nyckelmaterial och extraherade ljud ligger under
git-ignorerade artifacts. Inga filer har skickats till headsetet och inga
telefon-/headsetinställningar har ändrats av analysen.

## Direkt observerat

`bluetoothctl info 00:00:00:00:00:00` visar HD 350BT, paired/bonded och
connected. Adressen korrigerades efter en första felläsning av skärmbilden.
Enheten annonserar bland annat:

- `a2129ff3-081b-4c45-8afe-469d9c4842eb`
- `0000fdce-0000-1000-8000-00805f9b34fb`
- Device Information, Battery Service och vanliga ljudprofiler.
- Modalias `bluetooth:v000Ap0160dFFFF`.

Den första UUID:n motsvarar äldre GAIA SPP enligt appanalysen nedan.
Det är ett konkret transportspår, inte bevis för chipmodell, fungerande
OTA eller tillåtna modifierade paket. Ingen GAIA-fråga har skickats.
Ingen ADB-enhet var ansluten vid inventeringen.

## Publika källor och vad de faktiskt visar

- [Sennheiser produkt](https://us.sennheiser-hearing.com/products/hd-350bt):
  svart modell har artikelnummer 508384.
- [HD 350BT manual](https://media.graphassets.com/aDjmC7I7SCCfIF6FHmJx):
  firmwareuppdatering via Smart Control.
- [Smart Control-appanalys](https://github.com/xndbogdan/sennheiser-control/blob/main/PROTOCOL.md):
  version 4.9.3 innehåller JavaScript i `assets/app/bundle.js` och
  JSON-modellbeskrivningar. Dokumentet gäller huvudsakligen Momentum 4;
  dess GAIA v3-kommandon får inte antas gälla HD 350BT. Det dokumenterar
  även ovanstående äldre GAIA UUID. Detta ger en metod för statisk analys.
- [BTD600 API-analys](https://github.com/HomerSp/BTD600_Downgrade):
  dokumenterar konsumentfirmwareserverns release- och manifestanrop.
  BTD600-paket eller dess installationsmetod ska inte användas på HD 350BT.
- [FCC testrapport](https://fcc.report/FCC-ID/DMOSEBT4/4534522.pdf):
  SEBT3 är HD 350BT och SEBT4 är HD 450BT; rapporten anger skillnader i
  ANC, mikrofoner, line-in och batteri. Detta bevisar inte identisk firmware.
- [FCC internbilder 1](https://fccid.io/DMOSEBT4/Internal-Photos/Internal-Photos-1-4534545)
  och [internbilder 2](https://fccid.io/DMOSEBT4/Internal-Photos/Internal-Photos-2-4534546)
  är möjliga källor för chipidentifiering. Endast metadata gick att läsa;
  kretsmärkningar har inte granskats.

## Serverprov

Bas: `https://api.s-consumer-cloud.com/firmware/api/`.
Enstaka GET-anrop, ingen skanning eller skrivning:

| Sökväg | Resultat |
|---|---|
| `v2/availableSystemReleases/700248?os_type=android` | HTTP 200, BTD600-lista |
| `v2/availableSystemReleases/508384?os_type=android` | HTTP 400, success false |
| Samma v2-anrop med 508385, 352 eller HD350BT | HTTP 400 |
| `v1/availableSystemReleases/508384?os_type=android` | HTTP 404 |
| `v2/systemRelease/508384/5.8.0?os_type=android` | HTTP 400 |

400 betyder att dessa anrop inte fungerar, inte att originalfirmware saknas.
Använd rätt identifierare/anrop från appen innan fler serverprov.
APKPure-nedladdningar gav HTTP 403 och HTML, inte APK/XAPK. Ingen sådan
fil har installerats eller analyserats som en app.

## Rekommenderad arbetsordning

1. Installera vanliga Sennheiser Smart Control (`com.sennheiser.control`)
   från Google Play på användarens Androidtelefon. Anslut USB med
   USB-felsökning och godkänn datorns RSA-dialog.
2. Kör `adb devices`, välj rätt serienummer, läs sedan
   `adb -s SERIAL shell pm path com.sennheiser.control` och kopiera
   de returnerade APK-filerna med `adb -s SERIAL pull` till ignorerade
   `artifacts/original/hd350bt/app/`. Ingen root behövs för detta normalt.
   Spara SHA-256, appversion och signeringscertifikat där verktyg finns.
3. Läs APK offline som ZIP. Inventera `assets/app/`, leta efter HD350,
   HD450, SEBT3 och relevanta modellalias; läs bundle.js och modell-JSON.
   Fastställ firmware-ID, serveranrop, transport, GAIA-version och
   dokumenterade läskommandon. Exekvera inte appens JavaScript på värden.
4. Hämta rätt manifest och originalpaket från den officiella servern.
   Bevara originalbyte, URL, storlek, version och SHA-256. Analysera
   paketgränser, komprimering/kryptering, partitioner och röstresurser offline.
5. Avgör om röster levereras separat eller ingår i systempaketet.
   Identifiera codec, samplingsfrekvens, storleksgränser och alla CRC/hashar.
   Avgör framför allt vilka regioner som är digitalt signerade och var
   signaturen verifieras. En korrigerad CRC ersätter inte en signatur.
6. Om resurser kan byggas om: kräv byte-identisk roundtrip av stock,
   avkodning/återkodning av en originalprompt och oberoende validering.
   Återanvänd våra WAV-röster först när målformatet är känt; UGREENs WTS,
   UFW och boot-CRC är inte etablerade för denna modell.
7. Före fysisk skrivning: fastställ stock-återställning, versionsregler,
   banklayout och uppdateringsavbrottens konsekvenser. Gör ett separat,
   uttryckligt beslut om test av exakt modifierad fil och hash.

## Beslutsgrenar

- Separata, modifierbara röstresurser: bästa kandidaten; ändra en prompt.
- Osignerat ompackningsbart systempaket: möjligt efter integritetsanalys.
- Signerade röstresurser som verifieras i headsetet: vanlig ompackning
  räcker inte. Kontrollera först om en legitim separat resursväg finns.
- Ingen tillgänglig OTA-väg: hårdvaruläsning är ett senare spår efter
  chip-/testpunktsidentifiering och plan för två identiska originaldumpar.

Det finns ännu ingen verifierad metod för egna röster på HD 350BT.
Nästa konkreta artefakt är originalappen från telefonen, följd av rätt
modellbeskrivning och originalfirmware. UGREEN och Linocell är orörda.
