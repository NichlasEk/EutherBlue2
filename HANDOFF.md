# EutherBlue – verifierat HD 350BT-resultat

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
