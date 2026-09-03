# Linocell BTH13 – skrivskyddad chargestore/testbox-väg

Datum: 2026-09-03

Status: protokollet är avkodat offline; ingen elektrisk anslutning är gjord

## Slutsats

Den publika BR30-referensen innehåller inte bara chargestore-källkod utan även
en färdig, icke stripad `sdk.elf` och optimerad LLVM-bitkod. Därmed gick det att
återskapa protokollets faktiska ramning utan att sända något till en lur.

BR30-familjen använder en halvduplex UART på en enda konfigurerbar kontakt,
normalt `P00` i exempelboardarna. JieLis officiella dokumentation visar att
AC697x och senare normalt kan binda seriell uppgradering till `LDOIN`, samma
kontakt som används när luren sitter i ladd-/testfixturen. Detta är den starkaste
icke-destruktiva fysiska kandidaten för BTH13:s synliga guldkontakt.

Det är fortfarande en kandidat. Vi vet inte BTH13-kortets spänningsnivå,
LDOIN-kapacitans, exakta GPIO eller om Linocell-builden aktiverat testboxstödet.

## Återskapad ramning

Sänd ram:

```text
55 aa <payload_length> <payload...> <crc8>
```

CRC:n startar på 0 och kör varje bit LSB-först med polynom `0x8c` över sync,
längd och payload. Payload får vara högst 36 byte. Dekodern accepterar även
syncparet `5a a5`, vilket används för en alternativ ramtyp.

Tre rena läsfrågor finns under huvudkommando `0x21`:

| Fråga | Payload | Komplett ram |
|---|---|---|
| Bluetoothnamn | `21 01` | `55 aa 02 21 01 e1` |
| SDK-version | `21 02` | `55 aa 02 21 02 03` |
| Batterispänning/procent | `21 03` | `55 aa 02 21 03 5d` |

Svar återanvänder de två första payloadbyten och lägger till namn, versionssträng
eller två little-endian spänningsbyte plus procent.

Det lokala verktyget `tools/chargestore_readonly.py` kan skapa och validera
dessa ramar. Det har avsiktligt ingen seriell I/O och exponerar inga godtyckliga
payloads. Följande kommandon finns därför inte: factory reset `0x08`, DUT,
storage mode, TWS-adresskrivning eller update `0x20`.

```bash
./tools/chargestore_readonly.py encode sdk-version
./tools/chargestore_readonly.py decode 55aa02210203
```

## Bevis i den färdiga referensbilden

Den uppackade standardbildens `app.bin` innehåller bland annat loggsträngarna:

```text
[APP_CHARGESTORE]sub_cmd:%x
[APP_CHARGESTORE]get_verify_code
[APP_CHARGESTORE]rsp update_mask
[APP_CHARGESTORE]CMD_BOX_GET_TWS_PAIR_INFO
[APP_CHARGESTORE]version:%s ver_len:%x send_len:%x
```

Det visar att testboxhanteraren verkligen länkades in i referensbinären. Dess
SDK-strängar använder dessutom samma form som BTH13:s annonserade
`b2.3.5-@20221213-$dc9a`, även om referensbildens komponenter är daterade
2022-06-08. Detta stärker familjekopplingen men identifierar inte exakt build.

## Elektrisk säkerhetsgrind

En vanlig USB-TTL-adapter ska inte kopplas direkt till guldkontakten. Kontakten
kan samtidigt bära laddspänning, och en push-pull-TX kan kortsluta lurens eller
etuiets drivning. JieLis dokumentation anger dessutom att seriell kommunikation
över LDO kräver stöd i firmwaren och en LDOIN-kondensator mindre än `103`
(10 nF).

Säker första mätning är därför helt passiv:

1. högimpediv oscilloskopprob eller logikanalysator med gemensam GND;
2. mät tomgångsnivå och maximal spänning på laddkontakten;
3. fånga vad originaletuiet gör när den svarta offerluren sätts i och tas ur;
4. prova avkodning vid 9 600 baud och leta efter `55 aa`/`5a a5`;
5. anslut ingen sändande adapter förrän nivå, riktning och ramning är bekräftade.

Vid kontrollen av datorn fanns ingen `/dev/ttyUSB*` eller `/dev/ttyACM*`; endast
Bluetoothdongeln var ansluten. Därför gjordes inget elektriskt test denna gång.

## Källor

- [JieLis officiella guide för kabelbunden testboxuppgradering](https://doc.zh-jieli.com/Tools/zh-cn/mass_prod_tools/testbox_1tuo2/tb_wired_upgrade.html) – LDO/UART-krav, kondensatorgräns och testfixtur.
- [JieLis officiella guide för forcerad AC697x-uppgradering](https://doc.zh-jieli.com/Tools/zh-cn/dev_tools/forced_upgrade/upgrade_and_download.html) – anger LDOIN som seriell uppgraderingspin för AC697x och senare.
- [AC897N/AD697N earphone SDK V2.3.2](https://github.com/GZHXXY/AC897N_AD697N_earphone_release_V2.3.2) – chargestore-källkod, `sdk.elf`, LLVM-bitkod och färdig BR30-referensbild; analyserad vid commit `a55d953c15e4b9133d8b6b1bc95fabddb2922003`.
