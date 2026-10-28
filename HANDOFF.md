# EutherBlue – HD 350BT handoff

Uppdaterad 2026-10-28. Projekt: ~/EutherBlue.
Remote: https://github.com/NichlasEk/EutherBlue.git.

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

## AKTUELLT: resume-state prepare v3 lyckad, inväntar Power on

Första observeförsöket stoppade påför striktGAIA-notificationsvar0012.
Cleanup lyckades: nyckel4 borttagen(status05), reset0 ACK00. Verktyget är
rättat att acceptera00eller0012 förregistrering; syntetisk VM-eventparse
medACK testad. Nästa preparev2 timeouterade utanpaket; användaren slog
sedan påheadsetet ochpreparev3 lyckadesfullt:
resume-state-prepare-v3-20261028.json: version5.5.0,mode0,key4absent,
ny19ordscontext skrivenochverifierad,reset0 ACK00.

TESTKONTEXTEN FINNS NU ÅTER PÅ HEADSETET. Användaren ombedd tryckaPower on
och svaraklar. Nästakommando: python tools/probe_hd350_resume_state.py
--phase observe --execute --output artifacts/captures/hd350bt-usb/resume-state-observe-v2-20261028.json
Omavbrott: --phase cleanup raderar endast markeradnyckel ochreset0.
Inga firmwaredata/bankbyteskommandon har skickats. Full normalstatus ska
verifieras efter lyckadcleanup. Ingen öppen Bluetooth-session.

## AKTIVT PROV: tillfällig PS-nyckel4 för återupptagningskontroll

Användaren godkände fortsättning och startade om efter frågan om ett
begränsat PS-prov utan firmware/bankbyte. preparefasen lyckades:
nyckel4 varfrånvarande(status05), GAIAstore gav00, exakt19-ordsreadback
stämde ochGAIAreset0 gav00. Capture:
artifacts/captures/hd350bt-usb/resume-state-prepare-after-restart-20261028.json.
HEADSETET HAR NU EN TILLFÄLLIG UPPDATERINGSKONTEXT SOM SKA TAS BORT.

Verktyg tools/probe_hd350_resume_state.py:
--phase observe verifierar markerad kontext, ansluter upgrade, SYNC,
START endast omSYNC bekräftarresume2, frågar valideringsstatus, kopplar
från och raderar testnyckeln medreadback+reset0. --phase cleanup gör bara
ägarkontroll,radering,reset0. Egen markörid45555448, PS19ord, resumeord13=2.
Inga bilddata, START_DATA, TRANSFER_COMPLETE_RES, COMMIT, ABORT ellerERASE
finns i provsekvensen. Skicka INTE sådana kommandon; särskiltABORTkanradera.
Omobserveanslutningen inte fungerar: be omav/på och körobserve/cleanup.
Ingen slutlig normalstatus är ännu verifierad efterdenna preparefas.

Offlineunderlag: tools/audit_hd350_upgrade_resume.py kompilerar extraherad
referens-C medstubs. HandleReady är120/120byte matchad i stock0x14d5c4.
PRE_REBOOT väljerVALIDATED utanpartition-start. Två värdacceptkommandon
kan passera räknarspärren ireferenskoden; DETTA HAR INTE SKICKATS TILLHÅRDVARAN.
Stockappcall122476 gårtillUpgradeImageSwap14cce8. ROM-kontroll/nybank/rollback
ärfortfarande okända. Osignerad endastoffline testbild finns i
artifacts/build/hd350bt-UNSIGNED-OFFLINE-ONLY/ (bara prompt10utbytt).

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

## LIVE: PS-skrivning och ettordsflagga verifierade; återställning väntar

Efter användarens omstart rapporterade headsetet normalmode0 (fysisk av/på
lämnade alltså tidigaremode2). OriginalnyckelnFFFF001C stämde. GAIA0712
payload00c900aa gavstatus0 och0710 gav0000c900aa: ett ord00AA är faktiskt
skrivet och återläst. Reset0202/02 gavstatus0. Capture:
service-one-word-flag-after-restart-20261028.json. USB-inventeringen gav
fortsatt tre HID-interface/inget ALSA-kort: service-one-word-usb-20261028.json.
Återställningsförsöket timeouterade vidconnect innan några paket:
service-one-word-restore-20261028.json. Användaren har därför ombetts
starta om och svara klar för verifiering/återställning. Key201:s aktuella
värde efter uppstart är ännu okänt. Inga röster/firmwaredata skrivna.

Nästa klar: kör probe_hd350_service_flag.py --action restore --execute
--output medNYTT filnamn. Verktyget läser mode/key, återställer exakt
FFFF001C med verifierad readback; om mode redan0 görs ingen extrareset.
Denna PS-skrivförmåga är verifierad; flash-/röstskrivning är INTE det.

## Mode2 saknar extra USB-gränssnitt; ettordsflagga förberedd

Efter bekräftad USB ur/in syns fortfarande endast tre HID-interface.
Capturehidden-usb-audio-after-replug-20261028.json. Nästa hypotes:
uppstartens PsRetrieve201 begär1 ord, native servicekommandot lagrar2.
Förberett probe_hd350_service_flag.py --action enter skriver exakt00AA
som1 ord, läser tillbaka, och skickar GAIAreset0202/02 först efter match.
--action restore återställer ursprungsnyckelnFFFF001C och reset0202/00.
Matchad GAIAstorekälla använder PS_SIZE_ADJ((payload_length-2)/2), så
återställningspayload00c9ffff001c0000 inkluderar två paddingbyte för
2 PS-ord; obligatorisk readback före reset. Detta är en hypotesprövning,
inte en bekräftad korrigering eller flashupplåsning.
Första anslutningsförsöket timeouterade innan några paket/skrivningar:
service-one-word-flag-enter-20261028.json. Användaren ombedd starta om
headsetet och svara klar för försöket. Senaste uppmätta bootmode är2.

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

## Riktat prov av dolt USB-ljudläge förberett

Användaren har bett att ta sig in i läget. Verktyget
 tools/probe_hd350_hidden_usb_audio.py är förberett och offlinekontrollerat.
Det verifierar stockhash, HID-deskriptor, fysisk adress ochversion550,
skickar exakt ett report16-paket10883d och loggar USB-inventering20s.
Detta ÄR en beständig lägesändring via stockhandlerns PsStore/BootSetMode,
inte en skrivskyddad kontroll eller firmwareflashning. Ingen moderequest
har ännu skickats i detta avsnitt.

Återvägen GAIA0202 payload00 identifierades i kod: stockdispatcher15216c
matchar100/110 byte och köfunktionen151b8e matchar94/104 byte motreferensen.
 tools/restore_hd350_normal_boot.py kontrollerar version ochläge, läser
nyckel201 och återställer bootmode0 bara frånmode2. Det återställer inte
nyckel201:s andra ord. Verktyget är förberett, men fysisk återgång och
Bluetooth-tillgänglighet i det dolda läget är fortfarande oprövade.

USB anslöts på nytt och interface0 är nu/dev/hidraw7. Linux nekar rw.
Användaren har fått begäran sudo setfacl -m u:LOCAL_USER:rw /dev/hidraw7
med tydlig information om beständig flagga/omstart och oprövad återväg.
Nästa klar: kontrollera sysfs-identitet/ACL igen, kör det riktade provet,
utvärdera faktisk USB-återenumerering och läs mode/version via Bluetooth.

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

## Senaste resultat: skrivhandlers validerade, ingen röstskrivning

Se senaste avsnitt i reports/hd350bt-research-2026-10-28.md.
STORE_PS_KEY med tom payload gavINVALID_PARAMETER; inga nyckel-/databyte
skickades. OPEN_FILE i skrivläge gavINVALID_PARAMETER. OPEN_STORAGE_PARTITION
med tom payload gavNOT_SUPPORTED. Efterföljande version5.5.0 fungerade.
Fångst gaia-write-handler-validation-after-restart-20261028.json.
Stark binärmatchning visar PsStore-handlern; motsvarande direkta
partitionsskrivare saknas i matchad data-transfer-dispatch. Ingen beständig
skrivning utförd. Separata /rwfs/ och DEVICE_RO_FS API:er finns i SDK men
nåbar skrivväg i headsetet är inte funnen. Röstspelaren använder fasta
prompts/%d.prm-sökvägar. Utredningen är inte ett lyckat röstbyte.
Äldre retrieveUser0-label i capture var fel: request0258, medan ADKUSR0=028a.
Nästa arbete måste hitta en ny faktisk skrivväg; inga frågor/prov är nu väntande.

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

## Senaste enhetsprov: Enable USB Debug skickat

Efter användarens nya klar kördes det förberedda provet exakt en gång.
Fångst: artifacts/captures/hd350bt-usb/usb-debug-event-20261028.json.
Paketff010002000a07214109 skickat; efterföljande produktversion gav5.5.0.
USB-inventeringen ändrades inte under observationsfönstret. Detta bevisar
varken aktiverad debug eller att handlern är bortkompilerad. Ingen firmware,
PS-store, reset eller unlock-key-write skickades. Nästa fysiska kontroll:
USB ur/in medan headsetet förblir påslaget, därefter ny USB-inventering.
Den tidigare väntan på omstart nedan är historik; eventet ÄR nu skickat.

## Senaste framsteg: verklig filläsning; debugprov väntar på omstart

Användaren bad därefter om ett rejält försök att lösa firmwareprocessen.
Två omstarter och nya GAIA-prov genomförda. Röstfilen prompts/10.prm har
nu faktiskt lästs från headsetet:14464byte, SHA256
b95d9449e8975211af1016d97dca1ec79b9814cccba618818ce8d91b4d4baaf3,
byteidentisk med stock5.5.0. Sparad i artifacts/original/hd350bt/live-gaia-20261028/.
Det är inte en hel flashdump eller en skrivväg. CLOSE_FILE gavstatus3;
strömstängning ej bekräftad. RFCOMM behöver fortsatt ofta omstart mellan sessioner.

GAIA debugNOP och minnesstatus svarar success; bootmode0; API010205.
PS-läsning0258 gavINVALID_PARAMETER5, inte autentiseringsfel.
ADK6.4-testnyckeln är INTE samma nyckel som Sennheisers firmware verifieras med.

Nytt riktat spår: stockconfig enum Enable USB Debug=109 och ADK-event4109.
Referenshandlern (byggflaggsberoende) gör UsbDebugAllow(TRUE), cached till
curatorreset, fortfarande challenge-response. Handler i stock ej bevisad.
Verktyg tools/probe_hd350_usb_debug_event.py är färdigt och offlinekontrollerat.
Inget debugevent är ännu skickat. Pågående fråga till användaren: starta om
headsetet och svara klar för detta prov. Två tidigare 'klar' hör till tidigare
omstarter och får inte återanvändas för att anta att senaste omstarten är gjord.

Efter nytt klar, kör exakt en gång:
python tools/probe_hd350_usb_debug_event.py --send-debug-event --output artifacts/captures/hd350bt-usb/usb-debug-event-20261028.json
Kontrollerarprodukt5.5.0, skickarff010002000a07214109, läser version igen,
jämför USB-inventering. Ingen firmwaredata/PS-skrivning/reset/upplåsningsnyckel.
Om gränssnitt oförändrat: eventets exekvering är okänd, inte säkert avvisad.
Överväg USB ur/in med headsetet fortsatt på före slutsats om enumeration;
användarens fysiska hjälp behövs och detta är inte redan utfört.

Detaljer i senaste avsnittet i reports/hd350bt-research-2026-10-28.md.
Nya verktyg read_hd350_gaia_file.py och read_hd350_gaia_capabilities.py.
Inget customfirmware/röstbyte lyckat; ingen uppdateringsöverföring startad.

## Senaste fysiska kontroll efter återmontering

2026-10-28: användaren återanslöt headsetet och gav ACL på /dev/hidraw7.
USB1377:6012 hittades på bus002/device086, interface0–2 på hidraw7–9.
Efter kontroll av identitet och exakt HID-deskriptor skickades en version-
och en adressförfrågan. Båda gav samma svar som tidigare:5.5.0 och
00:00:00:00:00:00. Servicekommunikation fungerar efter återmonteringen.
Fångster: artifacts/captures/hd350bt-usb/service-{version,address}-reassembled-20261028.json.
Inga modebyten eller firmwareöverföringar. Detta ersätter USB-frånvaron i
inventeringen längst ned; övriga HID-gränssnitt har inte fått ny ACL.

## Senaste användarinstruktion och prioritet

Målet är att faktiskt byta headsetets inbyggda röster, som tidigare på UGREEN.
Det är INTE löst. Användaren bad om denna handoff eftersom utredningen blivit
ett kaninhål och har även en ASUS-laptop att laga (modell/fel ännu okänt).
Senaste styrning: användaren skruvar ihop headsetet och ansluter USB igen;
fortsatt forskning ska prioritera USB utan adapterbygge eller avlödning.
Användaren har ställbara regulatorer, många vanliga 5/3,3 V-komponenter och
lödutrustning, men ingen känd 1,8 V-adapter. Har inte bekräftat specifika
LM317/transistortyper. Hårdvaruspåret är vilande, inte beslutat genomförande.
Ingen bakgrundsforskning eller pågående mätprocess är startad vid handoff.

## Verifierat om headsetet

- Bluetooth: 00:00:00:00:00:00. Modell HD 350BT, produktfirmware 5.5.0.
- USB 1377:6012. Tidigare interface0 hidraw7: report16, 32 byte totalt;
  interface1 keyboard; interface2 hidraw9: AHI/upgrade. HID-numren och ACL
  ändras vid återanslutning: identifiera enheten igen innan varje prov.
- GAIA RFCOMM kanal1, tjänst a2129ff3-081b-4c45-8afe-469d9c4842eb.
  Version läst. GET_STORAGE_PARTITION_STATUS gav NOT_SUPPORTED. Ny RFCOMM
  anslutning kan nekas tills powercycle; upprepa inte meningslösa anslutningar.
- USB-serviceversion request 10 88 1c, nollutfylld till32 byte, svar
  10881c0000000000353530000000000000000000000000000000000000000000.
  ASCII550 i bytes8–10. Svaret behåller1c; tidigare hypotes2c var fel.
- USB-serviceadress request10 88 19, svar
  10881900000000000000000000000000000000000000000000000000000000.
  Matchar BlueZ-adressen. Dessa är verifierade läsningar, INTE flashåtkomst.
- AHI version0.4, modeNORMAL1. ConfigGet612/619 avvisat iNORMAL; inget
  modebyte gjort. Upgrade identity VERSION1,0,1; VARIANT8 nollbyte.
  Transport ansluten/frånkopplad; ingen firmwaredata överförd.
- Användaren återgav tidigare chipmärkningar via chattbild: QualcommQCC3034,
  MXIC X2106672NJ02, MX25U6432F. Ingen tydlig fysisk chipbild eller kapsling
  verifierad här. MX25U6432F är64Mbit/8MiB SPI NOR, VCC1,65–2,0V.

## Firmware och signatur – huvudblockeraren

Fyra officiella versioner5.4/5.5/5.6.2/5.8 hämtade/dekrypterade lokalt.
Firmware-ID300002. Rösterna i FileFS-sektion7 är identiska mellan versionerna.
13 prm-filer, SBC16kHz mono, bitpool60,128byte/8ms. Offlineprov med egen röst
finns men har aldrig överförts till headsetet.

Stock5.5: artifacts/extracted/hd350bt/firmware-5.5.0/HD350_firmware_v5.5.0.bin
SHA256 25dc3b7bbe73868a4ac1c54df12d1969512b35f4587e07c6359210afddf64c48.
RSA2048-PSS/SHA256, MGF1SHA256, salt222. Alla fyra original verifieras offline;
en enda ändrad byte i röst10 gör signaturen ogiltig. Signeringen omfattar
rådata i sektion0,1,4,5,6,7,9. Privat nyckel saknas.

Starka kodmatchningar i original5.5 visar ValidateFinish med hashfinalisering,
rsa_decrypt och PSS-verifiering. Det är mer än ett generiskt SDK-antagande,
men ingen modifierad firmware har skickats för fysisk acceptansprövning.
Uppdateraren kan radera/skriva andra banken INNAN signaturen kontrolleras.
SYNC kan spara PS-state; ABORT är inte bevisat ofarligt. Ingen säker fysisk
återställning är verifierad. Original-DFU är INTE fullständig enhetsbackup.
Skicka därför inte ändrad DFU bara för att testa om den avvisas.

## Statisk USB-kartläggning och nästa mjukvaruspår

Detaljer och källor: reports/hd350bt-research-2026-10-28.md (nyast överst).
Ignorerade referenser: artifacts/research/hd350bt/.
ADK6.4 länkad referens: adk642-reference/sink.elf med symboler/DWARF.
Länkad kod använder kompakta16/32-bitinstruktioner; objektfiler använder
expanderade instruktioner. Jämför inte dessa format som om de vore identiska.
REA ~/rea saknar konfigurerade analysproviders; lokal Ghidra saknar
Kalimba-stöd. Installera inte om REA utan ny anledning.

Stock5.5 filoffseter (inte fysiska flashadresser):
- sektion9 rådata börjar0x106a5c.
- usbHostHandleMessage0x12332a; report16-gren anropar0x12354c.
- servicehandler0x12354c..0x12385a. Grenar för clear-pairings, PsStore,
  BootSetMode, LED/charger/volume och konfigurationsskrivningar har hittats.
  Ingen generell flashläsning eller separat osignerad röstskrivning belagd.
- hjälpare0x119bf8 anropar kandidater configManagerGetWriteableConfig0x113fe4,
  ByteUtilsMemCpyPackString0x14f078 och UpdateWriteableConfig0x11400a.
  hjälpare0x11f8fa anropar samma configfunktioner. Exakta fält ej avkodade.
- UsbDebugAllow-kandidat0x16870e:37/50byte och ett unikt12byteankare.
  Inga direkta långa anrop hittade i skannat område. Kortanrop/tailcalls/
  indirekta vägar och felaktig matchning återstår; frånvaron bevisar inte
  att debug är omöjligt. Inget belagt debugaktiveringskommando ännu.

Nästa särskiljande forskning: verifiera denna kandidats anrop/alternativa
USB-debugvägar och faktisk servicekommandodispatch. Gör inte okända
kommandosvep. Behåll fungerande version/adress-läsningar som transportkontroll.
Decoderverktygen är partiella, kalibrerade mot kända länksymboler, inte en
full disassembler. Halvordsskanning kan ge falska anrop.

## Programmerare och senaste fysiska mätning

EutherCharge finns i /run/media/nichlas/Kingston1TB/EutherCharge.
Läs dess HANDOFF.md och docs/h6cs-independent-rails.md,
docs/h6cs-nyquest-chunks-prepared.md vid fortsatt programmerararbete.

TL866A kör vår modifierade Open-TL866 (1209:8661), inte stock/minipro.
Senast dokumenterade installerade bild:
artifacts/tl866-open-20261025-nyquest-chunks/ i EutherCharge.
ApplicationSHA2569dd45a21e6a45d5dd16a26d335a19ec3a296d7691b296da5a78d2f624ac5e917.
LAT-fix och egna native-läsrutiner finns. EutherCharge fick två identiska
2048x14-bit MCU-läsningar; detta bevisar inte1,8V-SPI-stöd.

2026-10-28 kördes tools/measure_tl866_lowest_vdd.py efter användarens
bekräftelse: tom sockel, inga adaptrar/ICSP-kablar, multimeter redo.
Befintlig firmware: i; v0; g0000008000; d0000000001; e1.
VDD endastZIF1, GNDZIF16,30sekunder. Användaren mätte **3,16 V**.
Avslut: d0; E0; e0; i, samtliga kvitterade; process exit0.
Fysisk avklingning till noll efter avstängning har INTE rapporterats.
Ingen programmerarfirmware ändrades i detta arbete.
Verktyget är offline utan --empty-socket-meter-ready. Använd inte igen utan
aktuell bekräftelse på tom sockel och redo mätare. Transportbortfall kan
förhindra shutdown; programmet säger då att USB måste dras ur.

Lokala byggkällor /tmp/h6cs-open-tl866/firmware/io.[ch]. VDD har8fasta steg;
lägsta dokumenterat2,99V. vdd_val sätter3digitala selectorbitar.
Radioman-schemat: Q4–Q6 kopplar motstånd i återkopplingen; grundnivån kan
höjas av dessa, ingen lägre1,8V-kombination identifierad. Att pulsera matningen
är inte bevis på stabil1,8V; multimeter visar inte korta toppar. Logiknivåerna
måste hanteras separat. EutherCharge har en äldre användarmätning3,9V på
GPIO13/14; utgå inte från att de säkert är3,3V.
Schemakopia /tmp/hd350-tl866-schematic.pdf, originalsida:
https://github.com/radiomanV/TL866/blob/master/docs/TL866.pdf

Andra tillgängliga programmerare:
- CH341A: finns enligt användaren, ej ansluten vid sista inventering.
  flashrom installerat, ch341a_spi finns. Chiplistan innehållerMX25U6435E/F,
  inte exaktMX25U6432F; kompatibilitet får inte bara antas för skrivning.
- GQ-4x4: finns enligt användaren; tillverkaren använderADP-099 för1,8V-SPI.
- Hemmabygge nyligen anslutet:1209:5432, Open Programmer USB HID,64byte
  endpoints. Identifierat genom USB-deskriptorer, INGA servicekommandon eller
  spänningsaktiveringar skickade. Eget kortutförande okänt; inga foton ännu.
  Projekt: https://openprog.altervista.org/ och https://pid.codes/1209/5432/.

## Vilande adapterförslag – inte byggt eller validerat

Föreslagen enkel SPI-väg: CH341A +1,8V-regulator och aktiv nivåomvandling.
TXU0304 (tre kanaler A→B, en B→A, båda rails1,1–5,5V) är lämpligare för
okänd3,3/5V-programmerare än tidigare nämnda AXC4T774 som INTE tål5V.
MCP1700-1802E/TO med rätt kondensatorer är en möjlig regulator. Alternativt
användarens justerbara regulator, vars modell fortfarande saknas.
LM317 kan principiellt ge1,8V; minlast/dropout/stabilitet måste dimensioneras.
Dioddropp i matningen löser varken reglering över last eller SPI-nivåerna.
Diskret transistorlösning för långsam SPI diskuterad men inget schema,
komponentval, hastighetskrav eller fysisk validering finns. Bygg inte efter
ett antagande om att den redan är färdigprojekterad.

## Filer och återupptagning

- reports/hd350bt-research-2026-10-28.md: huvudsaklig forskningslogg.
- artifacts/captures/hd350bt-usb/: faktiska protokollfångster.
- artifacts/research/hd350bt/source-search/: statiska matchningar/kalibreringar.
- tools/read_hd350_service_version.py: strikt whitelist version/adress.
- tools/decode_hd350_compact_calls.py och decode_hd350_usb_dispatch.py.
- tools/verify_hd350_signature.py och inspect_hd350_firmware.py.
- tools/measure_tl866_lowest_vdd.py: endast tom programmerare, fysisk mätning.

Arbetsträdet är smutsigt: .gitignore ändrad, researchrapport och flera tools
ospårade. Befintliga i.md och reports/images/ ska bevaras. Inget commit/push.
Proprietär firmware/dumpar stannar lokalt; publicera inte hemliga appnycklar.
Sista USB-inventeringen före användarens återanslutning visade TL866 och
Open Programmer, inte HD350. Kontrollera lsusb/sysfs/ACL vid återupptagning;
använd inte gamla hidraw- eller bus/device-nummer blint.

## 2026-10-28: Christian-banken fick COMMIT och COMPLETE via USB

Senaste verifierade resultat: den automatiska sekvensen lyckades på det
första USB-gränssnittet efter bankbytet (0a12:4007, input2). Headsetet
svarade SYNC resume 3/session d5f037da, START status 0, COMMIT_REQ 0f0000,
och efter COMMIT_CFM 10000100 kom COMPLETE_IND 120000. Capture innehåller
completed=true och commitCfmSent=true. Detta är en bekräftad commit på
protokollnivå. Efter begärd av/på-sekvens bekräftade användaren: ”funkar ju kanon!”.
Christian-rösten är därmed användarbekräftad efter commit. Samtliga 13
händelser är inte individuellt fysiskt verifierade.

Avgörande fångster i artifacts/captures/hd350bt-usb/:
- full-voice-candidate-stage-usb-fast-20261028.json
- rearm-first-interface-fixed-watch-retry-20261028.json
- first-interface-fixed-watch-20261028/first.json
- first-interface-fixed-watch-20261028/second.json
- first-interface-fixed-watch-20261028/commit.json

Kandidat: artifacts/build/hd350bt-Christian-Grosshandlare-full-UNSIGNED/HD350BT-5.5.0-Christian-Grosshandlare-full-UNSIGNED.bin
SHA256: d5f037dab3d64611696614a530833625f0cc8a8ad68c889a32ca0b8afe3384dd
Endast prompts/0.prm–12.prm ändrade, med ursprungliga storlekar och metadata.
Alla 13 prompter byggda med naturlig talhastighet. Bilden fram till APPUPFTR
staged; originalets signaturfooter skickades inte.

Tidigare slutsatser att signaturen blockerar normal commit eller att timing
är utesluten var felaktiga. 0x001e betyder LOADER_ERROR från
ImageUpgradeSwapTryStatus()==FALSE; det bevisar inte ett signaturfel.
Tidigare försök väntade på produkt-ID 1377:6012 och/eller en extra manuell
uppstart, och missade den första trialstarten. Originalets RSA-signatur är
ogiltig för ändrade prompter, men commit lyckades ändå enligt ovan.

Fungerande automatisering: tools/run_hd350_first_interface_commit.py.
Den kör första och andra TRANSFER_COMPLETE_RES och öppnar sedan direkt
charging-ID 0a12:4007 för SYNC -> START -> PROCEED -> invänta COMMIT_REQ ->
COMMIT_CFM -> COMPLETE. ACL-vakten tools/keep_hd350_acl.sh måste överleva
reenumerering; sed-läsningar har nu || continue så att set -e inte dödar den.

Senaste efterkontroll:
context-after-successful-first-interface-commit-20261028.json kunde inte
ansluta via Bluetooth (Host is down), inga värden ändrades. Användaren har därefter bekräftat fungerande röst. Ingen ny fysisk
åtgärd väntar. En ytterligare PS-statusläsning har inte genomförts.
Gör inte om rearm/staging/commit nu: bevara den lyckade banken och verifiera.
Hardwareverktyg måste köras utanför sandbox som annars döljer /dev.
Bluetooth: 00:00:00:00:00:00, RFCOMM kanal 1.
