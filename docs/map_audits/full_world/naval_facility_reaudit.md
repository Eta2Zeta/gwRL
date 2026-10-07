# Naval facilities — corrected proposed roster

**Rechecked 6 October 2026. Audit proposals only; production map unchanged.**

This is the proposed facility roster after reviewing the printed symbols again. It replaces the earlier conditional port-ID naming examples. A coast without a printed naval symbol has no printed facility. A named city, a railway, a convoy endpoint or an existing JSON field is not evidence that a port exists.

Each listed facility has a type, a territory, one physical ID and explicit sea accesses. Different symbols receive different IDs. Multiple accesses share an ID only when they belong to the same physical facility. Proposed IDs and source-finding references in the ledger are review aids; this report does not apply a new map schema.

Reviewed **295 territory records**, including **154 of 154** records with current naval-facility claims. **30** of those current records have an empty proposed naval inventory (including the retired Hispaniola aggregate). **3** territory reviews retain specific uncertainties.

Read [the source-reviewed ledger](data/naval_facility_reaudit.json) for exact IDs, evidence crops, reviewed sea zones and uncertainty details; [validation and counts](data/naval_facility_reaudit_summary.json) distinguish checked records from unresolved cases.

## How to read the comparison

“Current” reproduces the existing JSON, including incorrect sea IDs and facilities. “Proposed” lists the source-backed facility types and accesses. A deletion removes the facility claim, not a real coastline. Uncertain rows show only the settled facilities; the notes also need review before applying changes.

## Americas Atlantic

| Territory | Current naval facilities | Proposed naval facilities | Review |
|---|---|---|---|
| Bermuda (`land_bermuda`) | minor port → A31 | None | confirmed; AM-159 |
| Caatinga (`land_brazil_caatinga`) | minor port → A38 | minor port → A45; seaplane base → A45 | confirmed; AM-160 |
| Pampas (`land_brazil_pampas`) | minor port → A39 | None | confirmed; AM-162 |
| Rio de Janeiro (`land_brazil_rio_de_janeiro`) | minor port → A39 | major port → A47 | confirmed; AM-161 |
| Buenos Aires (`land_buenos_aires`) | minor port → A40 | minor shipyard → A49 | confirmed; AM-164 |
| British Columbia (`land_can_british_columbia`) | major port → P13; minor shipyard → P13 | major port → P13; minor shipyard → P13 | confirmed |
| Nova Scotia (`land_can_nova_scotia`) | major port → A18; minor shipyard → A18 | major port → A18; minor shipyard → A18 | confirmed |
| Ontario (`land_can_ontario`) | minor port → A1 | minor port → A1 | confirmed |
| Quebec (`land_can_quebec`) | minor port → A1; major port → A18; minor shipyard → A18 | minor port → A1; major port → A18; minor shipyard → A18 | confirmed |
| Chile (`land_chile`) | minor port → P31 | minor shipyard → P77; major port → P78 | confirmed; AM-151, AM-152 |
| Colombia (`land_colombia`) | minor port → A36 | minor port → A40 | confirmed; AM-148 |
| Cuba (`land_cuba`) | minor port → A36 | major port → A36 | confirmed; AM-157 |
| Ecuador (`land_ecuador`) | None | minor port → P76 | confirmed; AM-149 |
| French Guiana (`land_french_guiana`) | minor port → A38 | minor port → A41 | confirmed; AM-156 |
| Guyana (`land_guyana`) | minor port → A38 | minor port → A41 | confirmed; AM-154 |
| Hispaniola (`land_hispaniola`) | minor port → A36 | None | confirmed; AM-084 |
| Iceland (`land_iceland`) | None | minor port → A3 | confirmed; AM-243 |
| Eastern Mexico (`land_mex_eastern_mexico`) | None | minor port → A36 | confirmed; AM-146 |
| Western Mexico (`land_mex_western_mexico`) | minor port → P30, P31 | None | confirmed; AM-244 |
| Panama (`land_panama`) | minor port → A36, P31 | minor port → A40 | confirmed; AM-147, AM-172 |
| Patagonia (`land_patagonia`) | minor port → A40 | major port → A49 | confirmed; AM-165 |
| Peru (`land_peru`) | None | minor shipyard → P77; major port → P77 | confirmed; AM-150 |
| Puerto Rico (`land_puerto_rico`) | minor port → A36 | seaplane base → A41 | confirmed; AM-158 |
| Suriname (`land_suriname`) | minor port → A38 | None | confirmed; AM-155 |
| Uruguay (`land_uruguay`) | minor port → A39 | major port → A47 | confirmed; AM-163 |
| Great Lakes (`land_usa_great_lakes`) | minor port → A24 | minor port → A24 | confirmed |
| Midwest (`land_usa_midwest`) | None | minor port → A24 | confirmed; AM-134 |
| New England (`land_usa_new_england`) | None | minor shipyard → A25 | confirmed; AM-139 |
| New Orleans (`land_usa_new_orleans`) | minor port → A36 | major shipyard → A36 | confirmed; AM-144 |
| New York (`land_usa_new_york`) | minor port → A25 | major shipyard → A25 | confirmed; AM-140, AM-168 |
| Pacific Northwest (`land_usa_pacific_northwest`) | minor port → P6 | minor shipyard → P13 | confirmed; AM-136, AM-166 |
| San Francisco (`land_usa_san_francisco`) | minor port → P28 | major shipyard → P25 | confirmed; AM-137, AM-167 |
| Southeastern United States (`land_usa_southeastern_united_states`) | minor port → A31 | seaplane base → A36 | confirmed; AM-143 |
| Southwest United States (`land_usa_southwest_united_states`) | minor port → P30 | major shipyard → P25; seaplane base → P25 | confirmed; AM-138 |
| Texas (`land_usa_texas`) | None | minor shipyard → A36; major port → A36; seaplane base → A36 | confirmed; AM-145 |
| The Carolinas (`land_usa_the_carolinas`) | minor port → A26 | major shipyard → A30; seaplane base → A30 | confirmed; AM-142 |
| Washington, D.C. (`land_usa_washington_dc`) | minor port → A26 | major shipyard → A30 | confirmed; AM-141, AM-169 |
| Venezuela (`land_venezuela`) | minor port → A36 | major port → A41 | confirmed; AM-153 |

Also inspected with **no printed naval facilities**: Azores; Bahamas; Bolivia; Amazon Jungle; Alberta-Saskatchewan; Baffin Island; District of Keewatin; District of Mackenzie; Labrador; Manitoba; Newfoundland; Ottawa; Queen Charlotte Islands; St. Pierre Island; Yukon Territory; Central America; Dominican Republic; Falkland Islands; Faroe Islands; Galapagos; Greenland; Haiti; Jamaica; Leeward Islands; Netherlands Antilles; Paraguay; Rio Grande; Shetland Islands; Trinidad; Alaska; Usa Aleutian Islands; Appalachia; Chicago; Great Plains; Heartlands; Usa Kodiak Island; Southeast Alaska; Usa St Lawrence Island; The Northeast; Upper Midwest; Western United States; Windward Islands.

## Europe Africa Middle East

| Territory | Current naval facilities | Proposed naval facilities | Review |
|---|---|---|---|
| Aden (`land_aden`) | minor port → I3 | major port → I4 | confirmed; EA-324, EA-630 |
| Albania (`land_albania`) | minor port → M5 | minor port → M5 | confirmed; EA-605 |
| Angola (`land_angola`) | minor port → A39 | None | confirmed; EA-650 |
| Ascension (`land_ascension`) | None | minor dockyard → A50 | confirmed; EA-648 |
| British Somaliland (`land_british_somaliland`) | minor port → I4 | minor port → I4 | confirmed; EA-657 |
| Bulgaria (`land_bulgaria`) | minor port → M10 | minor port → M10 | confirmed; EA-611 |
| Cameroon (`land_cameroon`) | minor port → A38 | minor port → A51 | confirmed; EA-647 |
| Cape Town (`land_cape_town`) | minor port → A40 | minor dockyard → A54; unresolved details below | uncertain; EA-652 |
| Cyprus (`land_cyprus`) | None | minor port → M9 | confirmed; EA-299, EA-610 |
| Dahomey (`land_dahomey`) | minor port → A38 | minor port → A51 | confirmed; EA-645 |
| Denmark (`land_denmark`) | minor port → A10, A12, A23 | minor port → A10; minor shipyard → A12 | confirmed; EA-578 |
| Eritrea (`land_eritrea`) | minor port → I5 | minor port → I5 | confirmed; EA-659 |
| Basque Country (`land_esp_basque_country`) | minor port → A28 | None | confirmed; EA-592 |
| Catalonia (`land_esp_catalonia`) | major port → M1 | major port → M1 | confirmed; EA-593 |
| Eastern Andalucia (`land_esp_eastern_andalucia`) | minor shipyard → M2 | minor shipyard → M2 | confirmed; EA-594 |
| Galicia and Leon (`land_esp_galicia_and_leon`) | None | minor port → A28; major shipyard → A35 | confirmed; EA-591 |
| Western Andalucia (`land_esp_western_andalucia`) | major port → A44 | major port → A44 | confirmed; EA-595 |
| Estonia (`land_estonia`) | minor port → A12, A13 | minor shipyard → A14 | confirmed; EA-420, EA-586 |
| Fin Helsinki (`land_fin_helsinki`) | None | minor shipyard → A13, A14 | confirmed; EA-585 |
| Southern Finland (`land_fin_southern_finland`) | minor port → A13 | minor port → A13 | confirmed; EA-418, EA-584 |
| Aquitaine (`land_fra_aquitaine`) | minor port → A28 | major shipyard → A29; seaplane base → A29 | confirmed; EA-569 |
| Corsica (`land_fra_corsica`) | minor port → M3 | None | confirmed; EA-300, EA-301, EA-571 |
| Normandy (`land_fra_normandy`) | minor port → A23 | major shipyard → A21; major shipyard → A22 | confirmed; EA-567 |
| Picardy (`land_fra_picardy`) | minor port → A22, A23 | minor port → A22 | confirmed; EA-568 |
| Southern France (`land_fra_southern_france`) | minor port → A28, M1 | major shipyard → M1 | confirmed; EA-570 |
| French Morocco (`land_french_morocco`) | minor port → A28 | None | confirmed; EA-641 |
| French Somaliland (`land_french_somaliland`) | minor port → I5 | minor port → I4 | confirmed; EA-333, EA-658 |
| London (`land_gbr_london`) | minor port → A23 | major shipyard → A22, A23 | confirmed; EA-564 |
| Northern England (`land_gbr_northern_england`) | minor port → A21 | major shipyard → A6; major shipyard → A17 | confirmed; EA-562 |
| Gbr Northern Ireland (`land_gbr_northern_ireland`) | None | major shipyard → A17 | confirmed; EA-565 |
| Scotland (`land_gbr_scotland`) | minor port → A10, A6 | major port → A4, A6; major shipyard → A4; major shipyard → A6 | confirmed; EA-561 |
| Southern England (`land_gbr_southern_england`) | minor port → A21, A23 | minor dockyard → A17; major shipyard → A21; major shipyard → A22; seaplane base → A17; seaplane base → A23 | confirmed; EA-563 |
| Eastern Germany (`land_ger_eastern_germany`) | minor port → A12 | major shipyard → A12 | confirmed; EA-576 |
| Konigsberg (`land_ger_konigsberg`) | minor port → A12 | major shipyard → A12 | confirmed; EA-577 |
| Western Germany (`land_ger_western_germany`) | minor port → A12, A23 | major shipyard → A11; major shipyard → A12; seaplane base → A11; submarine base → A11 | confirmed; EA-575 |
| Gibraltar (`land_gibraltar`) | None | major dockyard → A44, M2 | confirmed; EA-597 |
| Gold Coast (`land_gold_coast`) | None | minor port → A51 | confirmed; EA-644 |
| Macedonia (`land_gre_macedonia`) | minor port → M5 | None | confirmed; EA-606 |
| Gre Peloponnese (`land_gre_peloponnese`) | None | minor port → M6, M7 | confirmed; EA-608 |
| Thessaly (`land_gre_thessaly`) | None | minor shipyard → M7 | confirmed; EA-607 |
| Southern Iran (`land_iran_southern_iran`) | minor port → I6, I7 | minor port → I6 | confirmed; EA-625 |
| Ireland (`land_ireland`) | minor port → A21, A22 | major dockyard → A17 | confirmed; EA-566 |
| Lazio (`land_ita_lazio`) | minor port → M4 | major shipyard → M3 | confirmed; EA-308, EA-600 |
| Northern Italy (`land_ita_northern_italy`) | minor port → M3 | major shipyard → M3; major shipyard → M5 | confirmed; EA-304, EA-305, EA-598 |
| Ita Rhodes (`land_ita_rhodes`) | None | minor port → M7 | confirmed; EA-609 |
| Rome (`land_ita_rome`) | minor port → M3 | seaplane base → M3; minor shipyard → M5 | confirmed; EA-306, EA-307, EA-599 |
| Sardinia (`land_ita_sardinia`) | minor port → M3 | None | confirmed; EA-302, EA-303, EA-572 |
| Ita Sicily (`land_ita_sicily`) | None | minor port → M3 | confirmed; EA-602 |
| Southern Italy (`land_ita_southern_italy`) | minor port → M4, M5 | minor shipyard → M3 | confirmed; EA-309, EA-601 |
| Italian Somaliland (`land_italian_somaliland`) | minor port → I4 | minor port → I3 | confirmed; EA-334, EA-335, EA-656 |
| Ivory Coast (`land_ivory_coast`) | None | minor port → A51 | confirmed; EA-643 |
| Kuwait (`land_kuwait`) | minor port → I7 | major port → I6 | confirmed; EA-321, EA-627 |
| Latvia (`land_latvia`) | None | major port → A14 | confirmed; EA-421, EA-422, EA-587 |
| Lower Egypt (`land_lower_egypt`) | minor port → I5, M9 | major dockyard → M8; major port → I5 | confirmed; EA-329, EA-330, EA-632 |
| Madagascar (`land_madagascar`) | minor port → I4 | major port → I3 | confirmed; EA-339, EA-340, EA-341, EA-660 |
| Malta (`land_malta`) | None | major dockyard → M4 | confirmed; EA-603 |
| Mauritius (`land_mauritius`) | minor port → I4 | minor port → I2 | confirmed; EA-342, EA-661 |
| Belgium (`land_neu_belgium`) | minor port → A23 | minor port → A23 | confirmed; EA-573 |
| Netherlands (`land_neu_netherlands`) | minor port → A23 | minor shipyard → A23 | confirmed; EA-574 |
| Nigeria (`land_nigeria`) | minor port → A38 | minor port → A51 | confirmed; EA-646 |
| Nor Northern Norway (`land_nor_northern_norway`) | None | major port → A8 | confirmed; EA-583 |
| Southern Norway (`land_nor_southern_norway`) | minor port → A10, A6 | minor port → A7; minor shipyard → A10 | confirmed; EA-412, EA-413, EA-581 |
| Trondelag (`land_nor_trondelag`) | minor port → A6 | None | confirmed; EA-414, EA-415, EA-582 |
| Northern Algeria (`land_northern_algeria`) | minor port → M2 | major port → M2 | confirmed; EA-639 |
| Oman (`land_oman`) | minor port → I6 | None | confirmed; EA-323, EA-629 |
| West Poland (`land_pol_west_poland`) | None | minor shipyard → A12 | confirmed; EA-424, EA-588 |
| Portugal (`land_portugal`) | None | minor shipyard → A35 | confirmed; EA-596 |
| Portuguese East Africa (`land_portuguese_east_africa`) | minor port → I4 | None | confirmed; EA-337, EA-654 |
| Qatar (`land_qatar`) | minor port → I7 | None | confirmed; EA-322, EA-628 |
| Bessarabia (`land_rom_bessarabia`) | minor port → M10 | None | confirmed; EA-613 |
| Central Romania (`land_rom_central_romania`) | None | minor shipyard → M10 | confirmed; EA-311, EA-612 |
| Saint Helena (`land_saint_helena`) | None | minor port → A53 | confirmed; EA-649 |
| Seychelles (`land_seychelles`) | minor port → I4 | minor port → I3 | confirmed; EA-343, EA-662 |
| Sierra Leone (`land_sierra_leone`) | None | major port → A48 | confirmed; EA-642 |
| South Africa (`land_south_africa`) | minor port → A40 | major port → I1 | confirmed; EA-338, EA-653 |
| Southern Iraq (`land_southern_iraq`) | minor port → I7 | None | confirmed; EA-626 |
| Southwest Africa (`land_southwest_africa`) | minor port → A39 | None | confirmed; EA-651 |
| Spanish Morocco (`land_spanish_morocco`) | minor port → A28 | minor port → A44 | confirmed; EA-640 |
| Gotaland (`land_swe_gotaland`) | minor port → A12, A13 | minor shipyard → A10 | confirmed; EA-417, EA-579 |
| Norrland (`land_swe_norrland`) | None | minor port → A13 | confirmed; EA-416, EA-580 |
| Syria (`land_syria`) | minor port → M9 | major port → M9 | confirmed; EA-319, EA-624 |
| Tanganyika (`land_tanganyika`) | minor port → I4 | major port → I3 | confirmed; EA-336, EA-655 |
| Tobruk (`land_tobruk`) | minor port → M8, M9 | minor port → M4, M8 | confirmed; EA-327, EA-635 |
| Transjordan (`land_transjordan`) | minor port → M9 | minor port → M8 | confirmed; EA-320, EA-631 |
| Tripoli (`land_tripoli`) | minor port → M4 | major port → M4 | confirmed; EA-325, EA-637 |
| Tripolitania (`land_tripolitania`) | None | minor port → M4 | confirmed; EA-326, EA-636 |
| Tunisia (`land_tunisia`) | minor port → M2 | minor port → M4 | confirmed; EA-638 |
| Akdeniz (`land_tur_akdeniz`) | None | minor port → M9 | confirmed; EA-318, EA-623 |
| Istanbul (`land_tur_istanbul`) | minor port → M10 | major port → M7; major port → M10; minor shipyard → M7 | confirmed; EA-621 |
| Karadeniz (`land_tur_karadeniz`) | minor port → M11 | minor port → M11 | confirmed; EA-622 |
| Upper Egypt (`land_upper_egypt`) | minor port → I5 | None | confirmed; EA-331, EA-633 |
| Crimea (`land_usr_crimea`) | minor port → M10, M11 | major shipyard → M11 | confirmed; EA-314, EA-616 |
| Donets-Kuban (`land_usr_donets_kuban`) | None | major port → M11 | confirmed; EA-315, EA-617 |
| Kalmytskaya (`land_usr_kalmytskaya`) | None | minor port → M12 | confirmed; EA-619 |
| Karelia (`land_usr_karelia`) | None | minor port → A9 | confirmed; EA-590 |
| Leningrad (`land_usr_leningrad`) | minor port → A12 | major shipyard → A14 | confirmed; EA-425, EA-589 |
| North-Caucasia (`land_usr_north_caucasia`) | minor port → M11 | seaplane base → M11 | confirmed; EA-618 |
| Southern Ukraine (`land_usr_southern_ukraine`) | None | major port → M10 | confirmed; EA-312, EA-614 |
| Taurida (`land_usr_taurida`) | minor port → M11 | minor shipyard → M11 | confirmed; EA-313, EA-615 |
| Transcaucasia (`land_usr_transcaucasia`) | minor port → M11 | minor port → M11; minor port → M12 | confirmed; EA-316, EA-620 |
| Western Egypt (`land_western_egypt`) | minor port → M9 | major port → M8 | confirmed; EA-328, EA-634 |
| Western Yugoslavia (`land_yug_western_yugoslavia`) | minor port → M5 | major port → M5; minor shipyard → M5 | confirmed; EA-310, EA-604 |

Also inspected with **no printed naval facilities**: Azerbaijan; Belgian Congo; Canary Islands; Cape Verde; Cyrenaica; Balearic Islands; Lapland; Viipuri Province; French Guinea; Gre Crete; Ifni; Northern Iran; Liberia; Lithuania; Mauritania; Nubia; Portuguese Guinea; Reunion; Rio De Oro; Sao Tome And Principe; Saudi Arabia; Svalbard; Eastern Anatolia; Northern Russia; Yemen.

## Asia Pacific

| Territory | Current naval facilities | Proposed naval facilities | Review |
|---|---|---|---|
| Annam-Tonkin (`land_annam_tonkin`) | minor port → P41 | minor port → P41 | confirmed |
| New South Wales (`land_aus_new_south_wales`) | minor port → P68 | minor shipyard → P72 | confirmed; AP-036, AP-069 |
| Northern Territory (`land_aus_northern_territory`) | minor port → P61 | seaplane base → P63 | confirmed; AP-069 |
| Queensland (`land_aus_queensland`) | minor port → P62 | minor port → P63 | confirmed; AP-069 |
| South Australia (`land_aus_south_australia`) | None | major port → P70 | confirmed; AP-069 |
| Aus Sydney (`land_aus_sydney`) | None | minor shipyard → P72 | confirmed; AP-036 |
| Tasmania (`land_aus_tasmania`) | minor port → P68 | None | confirmed; AP-069, AP-074 |
| Western Australia (`land_aus_western_australia`) | minor port → I6 | None | confirmed; AP-069, AP-101 |
| Borneo (`land_borneo`) | minor port → P59 | minor port → P60; seaplane base → P60 | confirmed; AP-068 |
| British Malaya (`land_british_malaya`) | major dockyard → P50 | major dockyard → P50 | confirmed |
| Burma (`land_burma`) | minor port → I11 | minor port → I11 | confirmed |
| Celebes (`land_celebes`) | minor port → P60 | None | confirmed; AP-100 |
| Beiping (`land_china_beiping`) | minor port → P14 | minor port → P14 | confirmed |
| Nanking (`land_china_nanking`) | major port → P14, P32 | major port → P14, P32 | confirmed |
| Shantung (`land_china_shantung`) | major port → P14; minor dockyard → P14 | major port → P14; minor dockyard → P14 | confirmed |
| Cochinchina (`land_cochinchina`) | major port → P50 | major port → P50 | confirmed |
| Dutch New Guinea (`land_dutch_new_guinea`) | minor port → P61 | None | confirmed; AP-100 |
| Fiji (`land_fiji`) | minor port → P65 | None | confirmed; AP-074 |
| Formosa (`land_formosa`) | major port → P32 | major port → P32 | confirmed |
| Guam (`land_guam`) | minor port → P43 | minor port → P43 | confirmed |
| Hong Kong (`land_hong_kong`) | major dockyard → P41 | major dockyard → P41 | confirmed |
| Calcutta (`land_india_calcutta`) | minor port → I11 | minor shipyard → I11; major port → I11 | confirmed; AP-052 |
| Ceylon (`land_india_ceylon`) | minor port → I11, I6 | major dockyard → I11 | confirmed; AP-052 |
| Maharashtra (`land_india_maharashtra`) | minor port → I6 | minor port → I6; major port → I6; major dockyard → I7 | confirmed; AP-052 |
| Southern India (`land_india_southern_india`) | minor port → I11, I6 | minor port → I11 | confirmed; AP-052 |
| Caroline Islands (`land_jap_caroline_islands`) | major port → access unassigned | major port → P46 | confirmed; AP-102 |
| Hokkaido (`land_jap_hokkaido`) | major port → P7 | major port → P7 | confirmed |
| Honshu (`land_jap_honshu`) | major shipyard → P15; major shipyard → P15; major port → P16 | major shipyard → P15; major shipyard → P15; major port → P16 | confirmed |
| Kyushu (`land_jap_kyushu`) | major port → P15; major shipyard → P15 | major port → P15; major shipyard → P15 | confirmed |
| Mariana Islands (`land_jap_mariana_islands`) | minor port → P43 | minor port → P43 | confirmed |
| Jap Marshall Islands (`land_jap_marshall_islands`) | None | minor port → P47 | confirmed; AP-075 |
| Okinawa (`land_jap_okinawa`) | minor port → P33; seaplane base → P33 | minor port → P33; seaplane base → P33 | confirmed |
| Tokyo (`land_jap_tokyo`) | major shipyard → P16 | major shipyard → P16 | confirmed |
| Java (`land_java`) | minor port → P59 | minor dockyard → P59 | confirmed; AP-068 |
| Korea (`land_korea`) | minor port → P14 | minor port → P14 | confirmed |
| Kwangtung (`land_kwangtung`) | major port → P41 | major port → P41 | confirmed |
| Luzon and the Visayas (`land_luzon_and_the_visayas`) | minor port → P42; submarine base → P50 | submarine base → P50; unresolved details below | uncertain; AP-066, AP-095, AP-103 |
| Rehe (`land_manchuria_rehe`) | major port → P14 | major port → P14 | confirmed |
| Mindanao (`land_mindanao`) | major port → P50; minor port → P52 | unresolved details below | uncertain; AP-066, AP-095, AP-103 |
| New Britain (`land_new_britain`) | minor port → P63 | major port → P53 | confirmed; AP-068 |
| New Caledonia (`land_new_caledonia`) | minor port → P65 | minor port → P73 | confirmed; AP-073 |
| New Guinea (`land_new_guinea`) | minor port → P63 | None | confirmed; AP-100 |
| New Hebrides (`land_new_hebrides`) | minor port → P65 | None | confirmed; AP-074 |
| North Island (`land_nz_north_island`) | minor port → P69 | major port → P73 | confirmed; AP-073 |
| South Island (`land_nz_south_island`) | minor port → P69 | None | confirmed; AP-073, AP-074 |
| Sumatra (`land_sumatra`) | minor port → P50, P59 | minor port → P50 | confirmed; AP-068 |
| Timor (`land_timor`) | minor port → P61 | None | confirmed; AP-100 |
| Usa Hawaii (`land_usa_hawaii`) | None | major dockyard → P29 | confirmed; AP-075 |
| Usa Midway (`land_usa_midway`) | None | minor port → P22; submarine base → P22 | confirmed; AP-075 |
| Wake Island (`land_usa_wake_island`) | minor port → P36 | None | confirmed; AP-074 |
| Kola (`land_usr_kola`) | minor port → A13 | minor shipyard → A8; major port → A8 | confirmed; AP-091 |
| Primorsky Krai (`land_usr_primorsky_krai`) | minor port → P7 | minor shipyard → P2, P7; major port → P7 | confirmed; AP-060 |
| South Sakhalin (`land_usr_south_sakhalin`) | minor port → P8 | None | confirmed; AP-059 |
| Usr Turkmenistan (`land_usr_turkmenistan`) | None | minor port → M12 | confirmed; AP-006 |

Also inspected with **no printed naval facilities**: Andaman Islands; Hopeh; Hunan; Easter Island; Gambier Islands; Gilbert Islands; Hainan; Bengal; Jap Bonin; Kurile Islands; Volcanic Islands; Lesser Sunda Islands; Line Islands; Maldive Islands; Maluku Islands; Palau; Pitcairn Island; Sarawak; Siam; Solomon Islands; Usa Attu And Kiska; Usa Samoa; Amur; Usr Big Diomede Island; Usr Chukotka; Usr Eastern Yakutia; Kamchatka; Magadan; North Sakhalin; Usr Samoyedia; Usr Vyatka; Usr Western Kazakhstan; Usr Yugria; Usr Zuryenia.

## Printed facilities with unresolved territory assignment

- `facility_philippines_p50_major_port_unassigned`: major port → P50; candidate territories: land_luzon_and_the_visayas, land_mindanao. This is one facility, not one copy in each candidate territory.

## Unresolved source details

### land_cape_town

- {"field": "map_vs_rule_example", "source": "game_content/rules/Global War 1936 v4.3 Rulebook.pdf", "printed_page": 16, "details": "The printed board clearly shows a white circled-anchor minor-dockyard symbol, while the supply-path example calls Cape Town a Minor Port. Expected facilities here transcribe the board symbol; reconcile edition/source precedence before applying a different type."}

### land_luzon_and_the_visayas

- {"facility_id": "facility_philippines_p50_major_port_unassigned", "issue": "land ownership of P50 major port", "candidate_land_ids": ["land_luzon_and_the_visayas", "land_mindanao"], "evidence": [{"source": "game_content/maps/gw36map.png", "rectangle": [6810, 2730, 7500, 3390], "crop": "evidence/ap_philippines_edges.png"}]}

### land_mindanao

- {"facility_id": "facility_philippines_p50_major_port_unassigned", "issue": "land ownership of P50 major port", "candidate_land_ids": ["land_luzon_and_the_visayas", "land_mindanao"], "evidence": [{"source": "game_content/maps/gw36map.png", "rectangle": [6810, 2730, 7500, 3390], "crop": "evidence/ap_philippines_edges.png"}]}


## Rebuild this comparison

Run `consolidate.py`, then `rebuild_naval_reaudit.py` from this directory using the repository Python environment. Both commands update audit artifacts only. The regional ledgers contain the actual source review; this script checks and presents those decisions without deriving geography from the old map.
