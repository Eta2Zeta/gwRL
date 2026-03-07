import json
from copy import deepcopy

OUTPUT = "gw36_manual_map.json"

DEFAULT_EDGE = {
    "neighbor_id": None,
    "border_terrain": "normal",
    "connecting_terrain": "normal",
    "has_river": False,
    "railway_connection": False,
    "railway_gauge": None,
    "port_or_dock_connection": False,
    "canal_or_strait": None,
    "narrow_crossing": False,
    "special_fortification": None,
    "inference_confidence": 0.7,
}

DEFAULT_NODE = {
    "id": None,
    "name": None,
    "type": "land",
    "terrain": "normal",
    "ipp_value": None,
    "original_owner": "Neutral",
    "current_owner": None,
    "is_capital": False,
    "is_victory_city": False,
    "source": "llm_manual_from_region_images",
    "source_confidence": 0.7,
    "neighbors": [],
}


def add_node(nodes, node_id, **attrs):
    if node_id in nodes:
        raise ValueError(f"Duplicate node id: {node_id}")

    node = deepcopy(DEFAULT_NODE)
    node["id"] = node_id
    node.update(attrs)
    if node["current_owner"] is None:
        node["current_owner"] = node["original_owner"]
    node["id"] = node_id
    node["name"] = node.get("name") or node_id
    node["neighbors"] = []
    nodes[node_id] = node
    return node


def set_edge(nodes, src, dst, **attrs):
    if src not in nodes or dst not in nodes:
        missing = [node_id for node_id in (src, dst) if node_id not in nodes]
        raise KeyError(f"Cannot set edge {src} -> {dst}; missing nodes: {missing}")

    node = nodes[src]
    for e in node["neighbors"]:
        if e["neighbor_id"] == dst:
            target = e
            break
    else:
        target = deepcopy(DEFAULT_EDGE)
        target["neighbor_id"] = dst
        node["neighbors"].append(target)

    for k, v in attrs.items():
        target[k] = v

    if target["railway_connection"] and not target["railway_gauge"]:
        target["railway_gauge"] = "narrow"


def link(nodes, a, b, **attrs):
    set_edge(nodes, a, b, **attrs)
    set_edge(nodes, b, a, **attrs)


def link_rail(nodes, a, b, border_terrain="normal", has_river=False, confidence=0.78):
    link(
        nodes,
        a,
        b,
        border_terrain=border_terrain,
        connecting_terrain=border_terrain,
        has_river=has_river,
        railway_connection=True,
        railway_gauge="narrow",
        inference_confidence=confidence,
    )


def link_land(nodes, a, b, border_terrain="normal", has_river=False, confidence=0.76):
    link(
        nodes,
        a,
        b,
        border_terrain=border_terrain,
        connecting_terrain=border_terrain,
        has_river=has_river,
        railway_connection=False,
        railway_gauge=None,
        port_or_dock_connection=False,
        canal_or_strait=None,
        narrow_crossing=False,
        inference_confidence=confidence,
    )


def link_land_sea(nodes, land, sea, port=False, canal=None, narrow=False, confidence=0.76):
    link(
        nodes,
        land,
        sea,
        border_terrain="coast",
        connecting_terrain="coast",
        has_river=False,
        railway_connection=False,
        railway_gauge=None,
        port_or_dock_connection=port,
        canal_or_strait=canal,
        narrow_crossing=narrow,
        inference_confidence=confidence,
    )


def build():
    doc = {
        "_meta": {
            "game": "Global War 1936 v4.3",
            "description": "LLM-manual map graph built tile-by-tile from divided region images and rulebook terrain/connection semantics.",
            "schema_notes": "Nodes are land/sea tiles. Neighbor edges encode terrain crossing, rivers, rail, ports/docks, and straits/canals used by RL action masking.",
            "build": {
                "source_images": [
                    "original_regions/europe_sub/europe_nw.png",
                    "original_regions/europe_sub/europe_ne.png",
                    "original_regions/europe_sub/europe_center.png",
                    "original_regions/europe_sub/europe_sw.png",
                    "original_regions/europe_sub/europe_se.png",
                ],
                "method": "manual_llm_transcription",
                "coverage": "manual_global_pass_v2",
            },
            "warnings": [
                "This file is manually transcribed from the map image and is intended for iterative RL environment development.",
                "Some IPP and terrain assignments remain best-effort where small labels were visually ambiguous.",
            ],
        },
        "nodes": {},
    }

    nodes = {}

    # Europe sea zones
    sea_nodes = [
        ("sea_a6", "Norwegian Sea"),
        ("sea_a7", "North Atlantic Approaches"),
        ("sea_a10", "Skagerrak"),
        ("sea_a11", "Kattegat"),
        ("sea_a12", "Baltic Sea"),
        ("sea_a13", "Gulf of Bothnia"),
        ("sea_a14", "Baltic East"),
        ("sea_a20", "Celtic Sea"),
        ("sea_a21", "Irish Sea"),
        ("sea_a22", "Bay of Biscay"),
        ("sea_a23", "English Channel"),
        ("sea_a28", "Western Mediterranean Approaches"),
        ("sea_a29", "Mid-Atlantic East"),
        ("sea_a44", "Strait of Gibraltar (Atlantic)"),
        ("sea_m1", "Western Mediterranean"),
        ("sea_m2", "Central Mediterranean"),
        ("sea_m3", "Tyrrhenian Sea"),
        ("sea_m4", "Ionian Sea"),
        ("sea_m5", "Adriatic Sea"),
        ("sea_m10", "Western Black Sea"),
        ("sea_m11", "Eastern Black Sea"),
        ("sea_m12", "Caspian Sea"),
        ("sea_m9", "Eastern Mediterranean"),
        ("sea_i3", "Red Sea"),
        ("sea_i4", "Somali Coast"),
        ("sea_i5", "Red Sea South"),
        ("sea_i6", "Arabian Sea"),
        ("sea_i7", "Persian Gulf"),
        ("sea_i11", "Bay of Bengal"),
        ("sea_a1", "Hudson Bay"),
        ("sea_a2", "Baffin Bay"),
        ("sea_a15", "Labrador Sea North"),
        ("sea_a18", "Labrador Sea South"),
        ("sea_a19", "North Atlantic North-West"),
        ("sea_a24", "Great Lakes Sea Zone"),
        ("sea_a25", "North Atlantic West"),
        ("sea_a26", "North Atlantic Central West"),
        ("sea_a31", "Bermuda Approaches"),
        ("sea_a33", "Western Atlantic Trade Lanes"),
        ("sea_a35", "Central Atlantic West"),
        ("sea_a36", "Caribbean Sea North"),
        ("sea_a38", "Central Atlantic Equatorial"),
        ("sea_a39", "South Atlantic North"),
        ("sea_a40", "South Atlantic South"),
        ("sea_p5", "Gulf of Alaska"),
        ("sea_p6", "North-East Pacific"),
        ("sea_p11", "North Pacific West"),
        ("sea_p12", "North Pacific Central"),
        ("sea_p13", "North Pacific East"),
        ("sea_p24", "North Pacific South-Central"),
        ("sea_p25", "North Pacific South-East"),
        ("sea_p28", "Pacific Off California"),
        ("sea_p30", "Eastern Pacific Tropical North"),
        ("sea_p31", "Eastern Pacific Tropical East"),
        ("sea_p2", "Sea of Okhotsk"),
        ("sea_p7", "Sea of Japan"),
        ("sea_p8", "Kurile Sea"),
        ("sea_p14", "Yellow Sea"),
        ("sea_p15", "East China Sea"),
        ("sea_p16", "Sea Zone P16"),
        ("sea_p32", "Philippine Sea West"),
        ("sea_p34", "Western Pacific Central"),
        ("sea_p50", "South China Sea"),
        ("sea_p52", "Philippine Sea South"),
        ("sea_p59", "Java Sea"),
        ("sea_p60", "Celebes Sea"),
        ("sea_p61", "Arafura Sea"),
        ("sea_p62", "Coral Sea"),
        ("sea_p63", "Bismarck Sea"),
        ("sea_p64", "Solomon Sea"),
        ("sea_p65", "Southwest Pacific"),
        ("sea_p68", "Tasman Sea"),
        ("sea_p69", "New Zealand Approaches"),
    ]
    for sid, name in sea_nodes:
        add_node(
            nodes,
            sid,
            name=name,
            type="sea",
            terrain="sea",
            ipp_value=None,
            original_owner="Neutral",
            source_confidence=0.8,
        )

    # Europe land nodes (manual from region images)
    land_nodes = [
        ("land_neu_netherlands", "Netherlands", "normal", 2, "Netherlands", False, False),
        ("land_neu_belgium", "Belgium", "normal", 2, "Belgium", False, False),
        ("land_ger_western_germany", "Western Germany", "normal", 4, "Germany", False, False),
        ("land_ger_eastern_germany", "Eastern Germany", "normal", 2, "Germany", False, False),
        ("land_ger_bavaria", "Bavaria", "normal", 3, "Germany", False, False),
        ("land_ger_berlin", "Berlin", "city", 8, "Germany", True, True),
        ("land_fra_normandy", "Normandy", "normal", 1, "France", False, False),
        ("land_fra_picardy", "Picardy", "normal", 2, "France", False, False),
        ("land_fra_paris", "Paris", "city", 3, "France", True, True),
        ("land_fra_aquitaine", "Aquitaine", "normal", 1, "France", False, False),
        ("land_fra_southern_france", "Southern France", "normal", 2, "France", False, False),
        ("land_fra_alsace_lorraine", "Alsace-Lorraine", "normal", 2, "France", False, False),
        ("land_gbr_scotland", "Scotland", "mountain_border", 2, "United Kingdom", False, False),
        ("land_gbr_northern_england", "Northern England", "normal", 3, "United Kingdom", False, False),
        ("land_gbr_southern_england", "Southern England", "normal", 2, "United Kingdom", False, False),
        ("land_gbr_london", "London", "city", 3, "United Kingdom", True, True),
        ("land_ireland", "Ireland", "normal", 2, "Ireland", False, False),
        ("land_ita_northern_italy", "Northern Italy", "normal", 4, "Italy", False, False),
        ("land_ita_lazio", "Lazio", "normal", 1, "Italy", False, False),
        ("land_ita_rome", "Rome", "city", 2, "Italy", True, True),
        ("land_ita_southern_italy", "Southern Italy", "normal", 2, "Italy", False, False),
        ("land_denmark", "Denmark", "normal", 1, "Denmark", True, True),
        ("land_nor_southern_norway", "Southern Norway", "mountain", 1, "Norway", False, False),
        ("land_nor_trondelag", "Trondelag", "mountain", 1, "Norway", False, False),
        ("land_swe_norrland", "Norrland", "tundra", 2, "Sweden", False, False),
        ("land_swe_gotland", "Gotland", "normal", 1, "Sweden", False, False),
        ("land_fin_lapland", "Lapland", "tundra", 1, "Finland", False, False),
        ("land_fin_southern_finland", "Southern Finland", "forest", 1, "Finland", True, True),
        ("land_fin_viipuri_province", "Viipuri Province", "forest", 1, "Finland", False, False),
        ("land_estonia", "Estonia", "normal", 1, "Estonia", False, False),
        ("land_latvia", "Latvia", "normal", 1, "Latvia", False, False),
        ("land_lithuania", "Lithuania", "normal", 1, "Lithuania", False, False),
        ("land_ger_konigsberg", "Konigsberg", "normal", 1, "Germany", False, False),
        ("land_pol_west_poland", "West Poland", "normal", 1, "Poland", False, False),
        ("land_pol_podlachia", "Podlachia", "normal", 1, "Poland", False, False),
        ("land_pol_lubelskie", "Lubelskie", "normal", 1, "Poland", False, False),
        ("land_pol_warsaw", "Warsaw", "city", 1, "Poland", True, True),
        ("land_pol_dolnoslaskie", "Dolnoslaskie", "normal", 1, "Poland", False, False),
        ("land_pol_east_poland", "East Poland", "normal", 1, "Poland", False, False),
        ("land_cze_bohemia", "Bohemia", "normal", 1, "Czechoslovakia", False, False),
        ("land_cze_slovakia", "Slovakia", "mountain", 1, "Czechoslovakia", False, False),
        ("land_aut_austria", "Austria", "mountain", 2, "Austria", True, False),
        ("land_hun_hungary", "Hungary", "normal", 2, "Hungary", True, False),
        ("land_rom_central_romania", "Central Romania", "mountain", 2, "Romania", False, False),
        ("land_rom_bessarabia", "Bessarabia", "normal", 1, "Romania", False, False),
        ("land_bulgaria", "Bulgaria", "normal", 1, "Bulgaria", True, False),
        ("land_yug_western_yugoslavia", "Western Yugoslavia", "mountain", 2, "Yugoslavia", False, False),
        ("land_yug_eastern_yugoslavia", "Eastern Yugoslavia", "mountain", 1, "Yugoslavia", True, False),
        ("land_albania", "Albania", "mountain", 1, "Albania", False, False),
        ("land_gre_macedonia", "Macedonia", "mountain", 1, "Greece", False, False),
        ("land_gre_thessaly", "Thessaly", "mountain", 1, "Greece", False, False),
        ("land_ita_sardinia", "Sardinia", "mountain", 1, "Italy", False, False),
        ("land_fra_corsica", "Corsica", "mountain", 1, "France", False, False),
        ("land_switzerland", "Switzerland", "mountain", 1, "Switzerland", False, False),
        ("land_esp_basque_country", "Basque Country", "mountain", 1, "Spain", False, False),
        ("land_esp_catalonia", "Catalonia", "mountain", 1, "Spain", False, False),

        ("land_tur_istanbul", "Istanbul", "city", 2, "Turkey", True, True),
        ("land_tur_karadeniz", "Karadeniz", "mountain", 0, "Turkey", False, False),
        ("land_tur_ankara", "Ankara", "mountain", 1, "Turkey", True, False),
        ("land_tur_akdeniz", "Akdeniz", "mountain", 0, "Turkey", False, False),
        ("land_tur_eastern_anatolia", "Eastern Anatolia", "mountain", 1, "Turkey", False, False),
        ("land_azerbaijan", "Azerbaijan", "mountain", 1, "Azerbaijan", False, False),

        ("land_usr_kola", "Kola", "tundra", 1, "Soviet Union", False, False),
        ("land_usr_karelia", "Karelia", "forest", 2, "Soviet Union", False, False),
        ("land_usr_northern_russia", "Northern Russia", "tundra", 1, "Soviet Union", False, False),
        ("land_usr_yaroslavl", "Yaroslavl", "normal", 1, "Soviet Union", False, False),
        ("land_usr_western_russia", "Western Russia", "normal", 1, "Soviet Union", False, False),
        ("land_usr_leningrad", "Leningrad", "city", 2, "Soviet Union", False, True),
        ("land_usr_moscow", "Moscow", "city", 4, "Soviet Union", True, True),
        ("land_usr_stalingrad", "Stalingrad", "city", 1, "Soviet Union", False, True),
        ("land_usr_gorky", "Gorky", "normal", 1, "Soviet Union", False, False),
        ("land_usr_smolensk", "Smolensk", "normal", 1, "Soviet Union", False, False),
        ("land_usr_northern_belorussia", "Northern Belorussia", "normal", 1, "Soviet Union", False, False),
        ("land_usr_southern_belorussia", "Southern Belorussia", "normal", 1, "Soviet Union", False, False),
        ("land_usr_western_ukraine", "Western Ukraine", "normal", 1, "Soviet Union", False, False),
        ("land_usr_kiev", "Kiev", "city", 0, "Soviet Union", False, True),
        ("land_usr_eastern_ukraine", "Eastern Ukraine", "normal", 1, "Soviet Union", False, False),
        ("land_usr_southern_ukraine", "Southern Ukraine", "normal", 1, "Soviet Union", False, False),
        ("land_usr_taurida", "Taurida", "normal", 1, "Soviet Union", False, False),
        ("land_usr_crimea", "Crimea", "normal", 1, "Soviet Union", False, False),
        ("land_usr_donets_kuban", "Donets-Kuban", "normal", 1, "Soviet Union", False, False),
        ("land_usr_kalmytskaya", "Kalmytskaya", "normal", 0, "Soviet Union", False, False),
        ("land_usr_north_caucasia", "North-Caucasia", "mountain", 3, "Soviet Union", False, False),
        ("land_usr_transcaucasia", "Transcaucasia", "mountain", 5, "Soviet Union", False, False),
        ("land_usr_tula_lipetsk", "Tula-Lipetsk", "normal", 1, "Soviet Union", False, False),
        ("land_usr_orel_kursk", "Orel-Kursk", "normal", 2, "Soviet Union", False, False),
        ("land_usr_saratov", "Saratov", "normal", 3, "Soviet Union", False, False),
        ("land_usr_kaluga_oblast", "Kaluga Oblast", "normal", 0, "Soviet Union", False, False),

        ("land_syria", "Syria", "normal", 1, "Syria", False, False),
        ("land_northern_iraq", "Northern Iraq", "desert", 1, "Iraq", False, False),
        ("land_southern_iraq", "Southern Iraq", "desert", 1, "Iraq", True, False),
        ("land_transjordan", "Transjordan", "desert", 0, "Transjordan", False, False),
        ("land_kuwait", "Kuwait", "desert", 0, "Kuwait", False, False),
        ("land_iran_northern_iran", "Northern Iran", "mountain", 1, "Iran", False, False),
        ("land_iran_southern_iran", "Southern Iran", "mountain", 2, "Iran", False, False),
        ("land_afghanistan", "Afghanistan", "mountain", 0, "Afghanistan", False, False),
        ("land_kashmir", "Kashmir", "mountain", 0, "Kashmir", False, False),
        ("land_tibet", "Tibet", "mountain", 0, "Tibet", False, False),
        ("land_nepal", "Nepal", "mountain", 0, "Nepal", False, False),
        ("land_india_punjab", "Punjab", "normal", 0, "British India", False, False),
        ("land_india_delhi", "Delhi", "city", 1, "British India", False, False),
        ("land_india_maharashtra", "Maharashtra", "normal", 1, "British India", False, False),
        ("land_india_benares", "Benares", "normal", 1, "British India", False, False),
        ("land_india_calcutta", "Calcutta", "city", 3, "British India", False, False),
        ("land_india_southern_india", "Southern India", "normal", 1, "British India", False, False),
        ("land_india_ceylon", "Ceylon", "normal", 0, "British India", False, False),
        ("land_burma", "Burma", "jungle", 1, "British India", False, False),
        ("land_saudi_arabia", "Saudi Arabia", "desert", 0, "Saudi Arabia", False, False),
        ("land_qatar", "Qatar", "desert", 0, "Qatar", False, False),
        ("land_oman", "Oman", "desert", 0, "Oman", False, False),
        ("land_aden", "Aden", "desert", 0, "United Kingdom", False, False),

        ("land_can_district_of_keewatin", "District of Keewatin", "tundra", 0, "Canada", False, False),
        ("land_can_baffin_island", "Baffin Island", "tundra", 0, "Canada", False, False),
        ("land_can_manitoba", "Manitoba", "normal", 1, "Canada", False, False),
        ("land_can_ontario", "Ontario", "normal", 2, "Canada", False, False),
        ("land_can_quebec", "Quebec", "normal", 1, "Canada", False, False),
        ("land_can_labrador", "Labrador", "normal", 1, "Canada", False, False),
        ("land_can_newfoundland", "Newfoundland", "normal", 1, "Canada", False, False),
        ("land_can_nova_scotia", "Nova Scotia", "normal", 1, "Canada", False, False),
        ("land_can_st_pierre_island", "St. Pierre Island", "normal", 0, "France", False, False),
        ("land_can_british_columbia", "British Columbia", "mountain", 1, "Canada", False, False),
        ("land_can_alberta_saskatchewan", "Alberta-Saskatchewan", "normal", 0, "Canada", False, False),

        ("land_usa_pacific_northwest", "Pacific Northwest", "forest", 1, "United States", False, False),
        ("land_usa_western_united_states", "Western United States", "mountain", 2, "United States", False, False),
        ("land_usa_southwest_united_states", "Southwest United States", "desert", 2, "United States", False, False),
        ("land_usa_great_plains", "Great Plains", "normal", 3, "United States", False, False),
        ("land_usa_upper_midwest", "Upper Midwest", "normal", 1, "United States", False, False),
        ("land_usa_midwest", "Midwest", "normal", 2, "United States", False, False),
        ("land_usa_great_lakes", "Great Lakes", "normal", 2, "United States", False, False),
        ("land_usa_heartlands", "Heartlands", "normal", 3, "United States", False, False),
        ("land_usa_the_northeast", "The Northeast", "normal", 5, "United States", False, False),
        ("land_usa_new_york", "New York", "city", 4, "United States", False, False),
        ("land_usa_washington_dc", "Washington, D.C.", "city", 5, "United States", True, False),
        ("land_usa_appalachia", "Appalachia", "mountain", 1, "United States", False, False),
        ("land_usa_the_carolinas", "The Carolinas", "normal", 2, "United States", False, False),
        ("land_usa_southeastern_united_states", "Southeastern United States", "normal", 2, "United States", False, False),
        ("land_usa_new_orleans", "New Orleans", "normal", 2, "United States", False, False),
        ("land_usa_texas", "Texas", "normal", 3, "United States", False, False),
        ("land_usa_chicago", "Chicago", "normal", 2, "United States", False, False),
        ("land_usa_san_francisco", "San Francisco", "city", 4, "United States", False, False),

        ("land_mex_western_mexico", "Western Mexico", "mountain", 0, "Mexico", False, False),
        ("land_mex_eastern_mexico", "Eastern Mexico", "normal", 1, "Mexico", False, False),
        ("land_central_america", "Central America", "jungle", 0, "Central America", False, False),
        ("land_panama", "Panama", "jungle", 2, "Panama", False, False),
        ("land_cuba", "Cuba", "normal", 1, "Cuba", False, False),
        ("land_hispaniola", "Hispaniola", "normal", 1, "Hispaniola", False, False),
        ("land_puerto_rico", "Puerto Rico", "normal", 0, "United States", False, False),
        ("land_bermuda", "Bermuda", "normal", 0, "United Kingdom", False, False),

        ("land_colombia", "Colombia", "mountain", 1, "Colombia", False, False),
        ("land_venezuela", "Venezuela", "normal", 1, "Venezuela", False, False),
        ("land_ecuador", "Ecuador", "mountain", 1, "Ecuador", False, False),
        ("land_peru", "Peru", "mountain", 1, "Peru", False, False),
        ("land_bolivia", "Bolivia", "mountain", 1, "Bolivia", False, False),
        ("land_brazil_amazon_jungle", "Amazon Jungle", "jungle", 1, "Brazil", False, False),
        ("land_brazil_caatinga", "Caatinga", "normal", 1, "Brazil", False, False),
        ("land_brazil_rio_de_janeiro", "Rio de Janeiro", "city", 1, "Brazil", False, False),
        ("land_brazil_pampas", "Pampas", "normal", 1, "Brazil", False, False),
        ("land_paraguay", "Paraguay", "normal", 1, "Paraguay", False, False),
        ("land_uruguay", "Uruguay", "normal", 1, "Uruguay", False, False),
        ("land_buenos_aires", "Buenos Aires", "city", 1, "Argentina", True, False),
        ("land_patagonia", "Patagonia", "normal", 1, "Argentina", False, False),
        ("land_chile", "Chile", "mountain", 1, "Chile", False, False),
        ("land_rio_grande", "Rio Grande", "normal", 1, "Argentina", False, False),
        ("land_guyana", "Guyana", "jungle", 0, "Guyana", False, False),
        ("land_suriname", "Suriname", "jungle", 0, "Suriname", False, False),
        ("land_french_guiana", "French Guiana", "jungle", 0, "France", False, False),

        ("land_french_morocco", "French Morocco", "mountain", 1, "France", False, False),
        ("land_spanish_morocco", "Spanish Morocco", "mountain", 0, "Spain", False, False),
        ("land_northern_algeria", "Northern Algeria", "mountain", 0, "France", False, False),
        ("land_western_algeria", "Western Algeria", "desert", 0, "France", False, False),
        ("land_southern_algeria", "Southern Algeria", "desert", 0, "France", False, False),
        ("land_tunisia", "Tunisia", "desert", 1, "France", False, False),
        ("land_tripoli", "Tripoli", "desert", 1, "Italy", False, False),
        ("land_tripolitania", "Tripolitania", "desert", 0, "Italy", False, False),
        ("land_cyrenaica", "Cyrenaica", "desert", 1, "Italy", False, False),
        ("land_tobruk", "Tobruk", "desert", 0, "Italy", False, False),
        ("land_western_egypt", "Western Egypt", "desert", 1, "Egypt", False, False),
        ("land_upper_egypt", "Upper Egypt", "desert", 0, "Egypt", False, False),
        ("land_lower_egypt", "Lower Egypt", "desert", 1, "Egypt", False, False),
        ("land_nubia", "Nubia", "desert", 1, "Egypt", False, False),
        ("land_eritrea", "Eritrea", "mountain", 0, "Italy", False, False),
        ("land_abyssinia", "Abyssinia", "mountain", 0, "Ethiopia", False, False),
        ("land_french_somaliland", "French Somaliland", "normal", 0, "France", False, False),
        ("land_british_somaliland", "British Somaliland", "desert", 0, "United Kingdom", False, False),
        ("land_italian_somaliland", "Italian Somaliland", "desert", 1, "Italy", False, False),
        ("land_sudan", "Sudan", "desert", 0, "United Kingdom", False, False),
        ("land_french_sudan", "French Sudan", "desert", 0, "France", False, False),
        ("land_niger", "Niger", "desert", 0, "France", False, False),
        ("land_chad", "Chad", "desert", 0, "France", False, False),
        ("land_dahomey", "Dahomey", "normal", 0, "France", False, False),
        ("land_nigeria", "Nigeria", "normal", 0, "United Kingdom", False, False),
        ("land_cameroon", "Cameroon", "jungle", 1, "France", False, False),
        ("land_oubangui_chari", "Oubangui-Chari", "jungle", 0, "France", False, False),
        ("land_belgian_congo", "Belgian Congo", "jungle", 1, "Belgium", False, False),
        ("land_angola", "Angola", "normal", 0, "Portugal", False, False),
        ("land_tanganyika", "Tanganyika", "normal", 0, "United Kingdom", False, False),
        ("land_rhodesia", "Rhodesia", "normal", 1, "United Kingdom", False, False),
        ("land_portuguese_east_africa", "Portuguese East Africa", "normal", 1, "Portugal", False, False),
        ("land_southwest_africa", "Southwest Africa", "desert", 0, "South Africa", False, False),
        ("land_bechuanaland", "Bechuanaland", "normal", 0, "South Africa", False, False),
        ("land_cape_town", "Cape Town", "normal", 1, "South Africa", False, False),
        ("land_south_africa", "South Africa", "normal", 1, "South Africa", False, False),
        ("land_madagascar", "Madagascar", "jungle", 1, "France", False, False),
        ("land_mauritius", "Mauritius", "normal", 0, "United Kingdom", False, False),
        ("land_seychelles", "Seychelles", "normal", 0, "United Kingdom", False, False),

        ("land_usr_stalino", "Stalino", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_vanavara", "Vanavara", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_irkutsk", "Irkutsk", "tundra", 1, "Soviet Union", False, False),
        ("land_usr_angara", "Angara", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_yakutsk", "Yakutsk", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_southern_yakutia", "Southern Yakutia", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_magadan", "Magadan", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_kamchatka", "Kamchatka", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_amur", "Amur", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_chita", "Chita", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_buryatia", "Buryatia", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_primorsky_krai", "Primorsky Krai", "tundra", 2, "Soviet Union", False, False),
        ("land_usr_north_sakhalin", "North Sakhalin", "tundra", 0, "Soviet Union", False, False),
        ("land_usr_south_sakhalin", "South Sakhalin", "tundra", 0, "Soviet Union", False, False),

        ("land_mongolia_tannu_tuva", "Tannu Tuva", "mountain", 0, "Mongolia", False, False),
        ("land_mongolia_kobdo", "Kobdo", "mountain", 0, "Mongolia", False, False),
        ("land_mongolia_ulyassutai", "Ulyassutai", "mountain", 0, "Mongolia", False, False),
        ("land_mongolia_central_mongolia", "Central Mongolia", "mountain", 0, "Mongolia", False, False),
        ("land_mongolia_kherlen", "Kherlen", "mountain", 1, "Mongolia", False, False),

        ("land_manchuria_northern", "Northern Manchuria", "normal", 1, "Japan", False, False),
        ("land_manchuria_western", "Western Manchuria", "normal", 1, "Japan", False, False),
        ("land_manchuria_eastern", "Eastern Manchuria", "normal", 1, "Japan", False, False),
        ("land_manchuria_rehe", "Rehe", "normal", 1, "Japan", False, False),
        ("land_china_suiyuan", "Suiyuan", "normal", 1, "China", False, False),
        ("land_china_hopeh", "Hopeh", "normal", 1, "China", False, False),
        ("land_china_beiping", "Beiping", "city", 2, "China", False, False),
        ("land_china_shantung", "Shantung", "normal", 2, "China", False, False),
        ("land_china_nanking", "Nanking", "city", 2, "China", False, False),
        ("land_china_hunan", "Hunan", "normal", 2, "China", False, False),
        ("land_china_shensi", "Shensi", "normal", 2, "China", False, False),
        ("land_china_szechwan", "Szechwan", "mountain", 2, "China", False, False),
        ("land_china_kweichow", "Kweichow", "mountain", 0, "China", False, False),
        ("land_china_yunnan", "Yunnan", "mountain", 1, "China", False, False),
        ("land_china_tsinghai", "Tsinghai", "mountain", 0, "China", False, False),
        ("land_china_sinkiang", "Sinkiang", "mountain", 0, "China", False, False),
        ("land_jap_tokyo", "Tokyo", "city", 3, "Japan", True, True),
        ("land_jap_honshu", "Honshu", "normal", 2, "Japan", False, False),
        ("land_jap_hokkaido", "Hokkaido", "forest", 1, "Japan", False, False),
        ("land_jap_kyushu", "Kyushu", "mountain", 1, "Japan", False, False),
        ("land_korea", "Korea", "mountain", 2, "Japan", False, False),
        ("land_formosa", "Formosa", "normal", 2, "Japan", False, False),
        ("land_hainan", "Hainan", "normal", 1, "Japan", False, False),
        ("land_hong_kong", "Hong Kong", "city", 2, "United Kingdom", False, False),
        ("land_kwangtung", "Kwangtung", "normal", 2, "China", False, False),
        ("land_kwangsi", "Kwangsi", "jungle", 0, "China", False, False),
        ("land_annam_tonkin", "Annam-Tonkin", "jungle", 1, "France", False, False),
        ("land_cochinchina", "Cochinchina", "jungle", 1, "France", False, False),
        ("land_siam", "Siam", "jungle", 1, "Siam", False, False),
        ("land_luzon_and_the_visayas", "Luzon and the Visayas", "jungle", 1, "Philippines", False, False),
        ("land_mindanao", "Mindanao", "jungle", 1, "Philippines", False, False),
        ("land_guam", "Guam", "normal", 0, "United States", False, False),
        ("land_palau", "Palau", "normal", 0, "Japan", False, False),

        ("land_sumatra", "Sumatra", "jungle", 2, "Netherlands", False, False),
        ("land_java", "Java", "jungle", 2, "Netherlands", False, False),
        ("land_borneo", "Borneo", "jungle", 2, "Netherlands", False, False),
        ("land_celebes", "Celebes", "jungle", 1, "Netherlands", False, False),
        ("land_timor", "Timor", "normal", 1, "Portugal", False, False),
        ("land_dutch_new_guinea", "Dutch New Guinea", "jungle", 1, "Netherlands", False, False),
        ("land_new_guinea", "New Guinea", "jungle", 1, "Australia", False, False),
        ("land_new_britain", "New Britain", "jungle", 1, "Australia", False, False),

        ("land_aus_western_australia", "Western Australia", "desert", 0, "Australia", False, False),
        ("land_aus_northern_territory", "Northern Territory", "desert", 0, "Australia", False, False),
        ("land_aus_south_australia", "South Australia", "desert", 0, "Australia", False, False),
        ("land_aus_queensland", "Queensland", "normal", 1, "Australia", False, False),
        ("land_aus_new_south_wales", "New South Wales", "normal", 2, "Australia", False, False),
        ("land_aus_tasmania", "Tasmania", "normal", 0, "Australia", False, False),
        ("land_nz_north_island", "North Island", "normal", 1, "New Zealand", False, False),
        ("land_nz_south_island", "South Island", "normal", 0, "New Zealand", False, False),
        ("land_new_caledonia", "New Caledonia", "normal", 0, "France", False, False),
        ("land_fiji", "Fiji", "normal", 0, "United Kingdom", False, False),
        ("land_new_hebrides", "New Hebrides", "normal", 0, "United Kingdom", False, False),
    ]

    for node_id, name, terrain, ipp, owner, cap, vc in land_nodes:
        add_node(
            nodes,
            node_id,
            name=name,
            type="land",
            terrain=terrain,
            ipp_value=ipp,
            original_owner=owner,
            current_owner=owner,
            is_capital=cap,
            is_victory_city=vc,
            source="llm_manual_from_region_images",
            source_confidence=0.76,
        )

    # Sea-sea framework (Europe basin)
    link(nodes, "sea_a6", "sea_a7", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_a7", "sea_a10", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_a10", "sea_a11", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.85)
    link(nodes, "sea_a11", "sea_a12", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.85)
    link(nodes, "sea_a12", "sea_a13", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.85)
    link(nodes, "sea_a13", "sea_a14", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a20", "sea_a21", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a21", "sea_a23", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.85)
    link(nodes, "sea_a22", "sea_a23", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.85)
    link(nodes, "sea_a22", "sea_a28", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a28", "sea_a29", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)

    link(nodes, "sea_m1", "sea_a44", border_terrain="sea", connecting_terrain="sea", canal_or_strait="Strait of Gibraltar", inference_confidence=0.9)
    link(nodes, "sea_m1", "sea_m2", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.86)
    link(nodes, "sea_m2", "sea_m3", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_m2", "sea_m4", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_m3", "sea_m5", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_m4", "sea_m5", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_m5", "sea_m10", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_m10", "sea_m11", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.88)
    link(nodes, "sea_m11", "sea_m12", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.78)
    link(nodes, "sea_m10", "sea_m9", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_m9", "sea_i3", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_i3", "sea_i5", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_i5", "sea_i4", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_i3", "sea_i6", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_i4", "sea_i6", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_i6", "sea_i7", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_i6", "sea_i11", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_a1", "sea_a2", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a2", "sea_a15", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a15", "sea_a18", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.86)
    link(nodes, "sea_a18", "sea_a19", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.86)
    link(nodes, "sea_a18", "sea_a25", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.86)
    link(nodes, "sea_a25", "sea_a26", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.86)
    link(nodes, "sea_a26", "sea_a31", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.86)
    link(nodes, "sea_a31", "sea_a33", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_a33", "sea_a35", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a35", "sea_a38", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a38", "sea_a39", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a39", "sea_a40", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_a36", "sea_a31", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_a36", "sea_a33", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)

    link(nodes, "sea_p5", "sea_p6", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p6", "sea_p11", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p11", "sea_p12", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p6", "sea_p12", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p12", "sea_p13", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p12", "sea_p24", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p13", "sea_p25", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p24", "sea_p25", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.8)
    link(nodes, "sea_p25", "sea_p28", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_p28", "sea_p30", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_p30", "sea_p31", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_p2", "sea_p7", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_p2", "sea_p8", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_p7", "sea_p14", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.82)
    link(nodes, "sea_p14", "sea_p15", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p15", "sea_p32", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p32", "sea_p34", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p15", "sea_p50", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p50", "sea_p52", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p50", "sea_p59", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p59", "sea_p60", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p60", "sea_p61", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p61", "sea_p62", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p62", "sea_p63", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p63", "sea_p64", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p64", "sea_p65", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p65", "sea_p68", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)
    link(nodes, "sea_p68", "sea_p69", border_terrain="sea", connecting_terrain="sea", inference_confidence=0.84)

    # Additional manual links
    link(nodes, "land_jap_tokyo", "sea_p16", border_terrain="coast", connecting_terrain="coast", port_or_dock_connection=True, inference_confidence=0.7)
    link(nodes, "land_jap_honshu", "sea_p16", border_terrain="coast", connecting_terrain="coast", port_or_dock_connection=True, inference_confidence=0.7)
    link(nodes, "land_jap_honshu", "land_jap_hokkaido", border_terrain="normal", connecting_terrain="normal", railway_connection=True, railway_gauge="narrow", inference_confidence=0.65)
    link(nodes, "land_jap_honshu", "land_jap_kyushu", border_terrain="normal", connecting_terrain="normal", railway_connection=True, railway_gauge="narrow", inference_confidence=0.65)

    link(nodes, "land_usa_new_york", "land_usa_chicago", border_terrain="normal", connecting_terrain="normal", railway_connection=True, railway_gauge="broad", inference_confidence=0.66)
    link(nodes, "land_usa_san_francisco", "land_usa_chicago", border_terrain="normal", connecting_terrain="normal", railway_connection=True, railway_gauge="broad", inference_confidence=0.66)

    # Core Western Europe land adjacencies
    link_rail(nodes, "land_neu_netherlands", "land_neu_belgium")
    link_rail(nodes, "land_neu_netherlands", "land_ger_western_germany")
    link_rail(nodes, "land_neu_belgium", "land_ger_western_germany")
    link_rail(nodes, "land_neu_belgium", "land_fra_picardy")

    link_rail(nodes, "land_ger_western_germany", "land_ger_eastern_germany")
    link_rail(nodes, "land_ger_western_germany", "land_ger_bavaria")
    link_rail(nodes, "land_ger_eastern_germany", "land_ger_berlin")
    link_rail(nodes, "land_ger_eastern_germany", "land_ger_bavaria")
    link_rail(nodes, "land_ger_eastern_germany", "land_ger_konigsberg")
    link_rail(nodes, "land_ger_eastern_germany", "land_pol_west_poland", has_river=True)

    link_rail(nodes, "land_ger_bavaria", "land_cze_bohemia")
    link_rail(nodes, "land_ger_bavaria", "land_aut_austria", border_terrain="mountain")
    link_rail(nodes, "land_ger_bavaria", "land_switzerland", border_terrain="mountain")
    link_rail(nodes, "land_ger_bavaria", "land_fra_alsace_lorraine", border_terrain="normal")

    link_rail(nodes, "land_fra_normandy", "land_fra_picardy")
    link_rail(nodes, "land_fra_normandy", "land_fra_paris")
    link_rail(nodes, "land_fra_picardy", "land_fra_paris")
    link_rail(nodes, "land_fra_paris", "land_fra_aquitaine")
    link_rail(nodes, "land_fra_paris", "land_fra_southern_france")
    link_rail(nodes, "land_fra_paris", "land_fra_alsace_lorraine")
    link_rail(nodes, "land_fra_aquitaine", "land_fra_southern_france")
    link_rail(nodes, "land_fra_alsace_lorraine", "land_fra_southern_france")
    link_rail(nodes, "land_fra_alsace_lorraine", "land_ger_western_germany", has_river=True)

    link_rail(nodes, "land_fra_southern_france", "land_ita_northern_italy", border_terrain="mountain")
    link_rail(nodes, "land_fra_southern_france", "land_switzerland", border_terrain="mountain")
    link_rail(nodes, "land_switzerland", "land_ita_northern_italy", border_terrain="mountain")

    link_rail(nodes, "land_ita_northern_italy", "land_ita_rome")
    link_rail(nodes, "land_ita_northern_italy", "land_ita_lazio")
    link_rail(nodes, "land_ita_rome", "land_ita_lazio")
    link_rail(nodes, "land_ita_lazio", "land_ita_southern_italy")
    link_rail(nodes, "land_ita_rome", "land_ita_southern_italy")

    # Scandinavia + Baltic
    link_rail(nodes, "land_nor_trondelag", "land_nor_southern_norway", border_terrain="mountain")
    link_land(nodes, "land_nor_trondelag", "land_swe_norrland", border_terrain="tundra", confidence=0.72)
    link(nodes, "land_nor_southern_norway", "land_denmark", border_terrain="coast", connecting_terrain="coast", narrow_crossing=True, inference_confidence=0.78)

    link_rail(nodes, "land_swe_norrland", "land_swe_gotland")
    link_rail(nodes, "land_swe_norrland", "land_fin_lapland")
    link_rail(nodes, "land_swe_norrland", "land_fin_southern_finland")

    link_rail(nodes, "land_fin_lapland", "land_fin_southern_finland")
    link_rail(nodes, "land_fin_southern_finland", "land_fin_viipuri_province")
    link_rail(nodes, "land_fin_viipuri_province", "land_usr_karelia")

    link_rail(nodes, "land_estonia", "land_latvia")
    link_rail(nodes, "land_latvia", "land_lithuania")
    link_rail(nodes, "land_lithuania", "land_pol_podlachia")
    link_rail(nodes, "land_lithuania", "land_pol_west_poland")
    link_rail(nodes, "land_lithuania", "land_ger_konigsberg")

    link_rail(nodes, "land_ger_konigsberg", "land_pol_west_poland")

    # Poland / Central Europe
    link_rail(nodes, "land_pol_west_poland", "land_pol_warsaw")
    link_rail(nodes, "land_pol_west_poland", "land_pol_podlachia")
    link_rail(nodes, "land_pol_west_poland", "land_pol_dolnoslaskie")
    link_rail(nodes, "land_pol_west_poland", "land_cze_bohemia")

    link_rail(nodes, "land_pol_warsaw", "land_pol_podlachia")
    link_rail(nodes, "land_pol_warsaw", "land_pol_lubelskie")
    link_rail(nodes, "land_pol_warsaw", "land_pol_dolnoslaskie")
    link_rail(nodes, "land_pol_warsaw", "land_pol_east_poland")

    link_rail(nodes, "land_pol_podlachia", "land_pol_lubelskie")
    link_rail(nodes, "land_pol_podlachia", "land_usr_northern_belorussia")

    link_rail(nodes, "land_pol_lubelskie", "land_pol_east_poland")
    link_rail(nodes, "land_pol_lubelskie", "land_usr_southern_belorussia")
    link_rail(nodes, "land_pol_lubelskie", "land_usr_western_ukraine")

    link_rail(nodes, "land_pol_dolnoslaskie", "land_pol_east_poland")
    link_rail(nodes, "land_pol_dolnoslaskie", "land_cze_bohemia")
    link_rail(nodes, "land_pol_dolnoslaskie", "land_cze_slovakia", border_terrain="mountain")

    link_rail(nodes, "land_pol_east_poland", "land_usr_western_ukraine")
    link_rail(nodes, "land_pol_east_poland", "land_cze_slovakia", border_terrain="mountain")

    link_rail(nodes, "land_cze_bohemia", "land_cze_slovakia", border_terrain="mountain")
    link_rail(nodes, "land_cze_bohemia", "land_aut_austria", border_terrain="mountain")

    link_rail(nodes, "land_cze_slovakia", "land_aut_austria", border_terrain="mountain")
    link_rail(nodes, "land_cze_slovakia", "land_hun_hungary")
    link_rail(nodes, "land_cze_slovakia", "land_rom_central_romania", border_terrain="mountain")

    link_rail(nodes, "land_aut_austria", "land_hun_hungary")
    link_rail(nodes, "land_aut_austria", "land_yug_western_yugoslavia", border_terrain="mountain")
    link_rail(nodes, "land_aut_austria", "land_ita_northern_italy", border_terrain="mountain")

    link_rail(nodes, "land_hun_hungary", "land_rom_central_romania")
    link_rail(nodes, "land_hun_hungary", "land_yug_western_yugoslavia")
    link_rail(nodes, "land_hun_hungary", "land_yug_eastern_yugoslavia")

    link_rail(nodes, "land_rom_central_romania", "land_rom_bessarabia")
    link_rail(nodes, "land_rom_central_romania", "land_bulgaria")
    link_rail(nodes, "land_rom_central_romania", "land_yug_eastern_yugoslavia")

    link_rail(nodes, "land_rom_bessarabia", "land_usr_western_ukraine")
    link_rail(nodes, "land_rom_bessarabia", "land_usr_southern_ukraine", has_river=True)

    link_rail(nodes, "land_bulgaria", "land_yug_eastern_yugoslavia")
    link_rail(nodes, "land_bulgaria", "land_gre_macedonia", border_terrain="mountain")
    link_rail(nodes, "land_bulgaria", "land_tur_istanbul")

    link_rail(nodes, "land_yug_western_yugoslavia", "land_yug_eastern_yugoslavia", border_terrain="mountain")
    link_rail(nodes, "land_yug_western_yugoslavia", "land_albania", border_terrain="mountain")
    link_rail(nodes, "land_yug_eastern_yugoslavia", "land_albania", border_terrain="mountain")
    link_rail(nodes, "land_yug_eastern_yugoslavia", "land_gre_macedonia", border_terrain="mountain")

    link_rail(nodes, "land_gre_macedonia", "land_gre_thessaly", border_terrain="mountain")
    link_rail(nodes, "land_gre_macedonia", "land_tur_istanbul")

    # Turkey + Caucasus
    link_rail(nodes, "land_tur_istanbul", "land_tur_karadeniz")
    link_rail(nodes, "land_tur_istanbul", "land_tur_ankara")
    link_rail(nodes, "land_tur_istanbul", "land_tur_akdeniz")
    link_rail(nodes, "land_tur_ankara", "land_tur_karadeniz")
    link_rail(nodes, "land_tur_ankara", "land_tur_akdeniz")
    link_rail(nodes, "land_tur_ankara", "land_tur_eastern_anatolia", border_terrain="mountain")
    link_rail(nodes, "land_tur_akdeniz", "land_tur_eastern_anatolia", border_terrain="mountain")
    link_rail(nodes, "land_tur_eastern_anatolia", "land_usr_transcaucasia", border_terrain="mountain")
    link_rail(nodes, "land_tur_eastern_anatolia", "land_azerbaijan", border_terrain="mountain")
    link_rail(nodes, "land_azerbaijan", "land_usr_transcaucasia", border_terrain="mountain")

    # Middle East + India
    link_rail(nodes, "land_tur_eastern_anatolia", "land_syria", border_terrain="mountain")
    link_rail(nodes, "land_tur_eastern_anatolia", "land_northern_iraq", border_terrain="mountain")
    link_rail(nodes, "land_northern_iraq", "land_southern_iraq")
    link_rail(nodes, "land_northern_iraq", "land_iran_northern_iran", border_terrain="mountain")
    link_rail(nodes, "land_southern_iraq", "land_iran_southern_iran")
    link_rail(nodes, "land_southern_iraq", "land_kuwait")
    link_rail(nodes, "land_southern_iraq", "land_transjordan")
    link_rail(nodes, "land_syria", "land_transjordan")
    link_rail(nodes, "land_syria", "land_northern_iraq")
    link_rail(nodes, "land_iran_northern_iran", "land_iran_southern_iran", border_terrain="mountain")
    link_rail(nodes, "land_iran_northern_iran", "land_afghanistan", border_terrain="mountain")
    link_rail(nodes, "land_iran_northern_iran", "land_azerbaijan", border_terrain="mountain")
    link_rail(nodes, "land_iran_southern_iran", "land_afghanistan", border_terrain="mountain")
    link_rail(nodes, "land_iran_southern_iran", "land_india_punjab", border_terrain="mountain")
    link_rail(nodes, "land_afghanistan", "land_kashmir", border_terrain="mountain")
    link_rail(nodes, "land_afghanistan", "land_india_punjab")
    link_rail(nodes, "land_kashmir", "land_tibet", border_terrain="mountain")
    link_rail(nodes, "land_kashmir", "land_nepal", border_terrain="mountain")
    link_rail(nodes, "land_kashmir", "land_india_punjab")
    link_rail(nodes, "land_tibet", "land_nepal", border_terrain="mountain")
    link_rail(nodes, "land_india_punjab", "land_india_delhi")
    link_rail(nodes, "land_india_delhi", "land_india_maharashtra")
    link_rail(nodes, "land_india_delhi", "land_india_benares")
    link_rail(nodes, "land_india_benares", "land_india_calcutta")
    link_rail(nodes, "land_india_benares", "land_burma", border_terrain="jungle")
    link_rail(nodes, "land_india_maharashtra", "land_india_southern_india")
    link_rail(nodes, "land_india_maharashtra", "land_india_benares")
    link_rail(nodes, "land_india_southern_india", "land_india_calcutta")
    link_rail(nodes, "land_burma", "land_india_calcutta", border_terrain="jungle")

    # North America
    link_rail(nodes, "land_can_district_of_keewatin", "land_can_manitoba")
    link_rail(nodes, "land_can_manitoba", "land_can_ontario")
    link_rail(nodes, "land_can_ontario", "land_can_quebec")
    link_rail(nodes, "land_can_quebec", "land_can_labrador")
    link_rail(nodes, "land_can_labrador", "land_can_newfoundland")
    link_rail(nodes, "land_can_newfoundland", "land_can_st_pierre_island")
    link_rail(nodes, "land_can_quebec", "land_can_nova_scotia")
    link_rail(nodes, "land_can_nova_scotia", "land_can_st_pierre_island")
    link_rail(nodes, "land_can_manitoba", "land_can_alberta_saskatchewan")
    link_rail(nodes, "land_can_alberta_saskatchewan", "land_can_british_columbia", border_terrain="mountain")
    link(nodes, "land_can_baffin_island", "land_can_labrador", border_terrain="coast", connecting_terrain="coast", narrow_crossing=True, inference_confidence=0.72)

    link_rail(nodes, "land_usa_pacific_northwest", "land_usa_western_united_states", border_terrain="mountain")
    link_rail(nodes, "land_usa_western_united_states", "land_usa_southwest_united_states", border_terrain="mountain")
    link_rail(nodes, "land_usa_western_united_states", "land_usa_great_plains")
    link_rail(nodes, "land_usa_pacific_northwest", "land_usa_upper_midwest")
    link_rail(nodes, "land_usa_upper_midwest", "land_usa_great_lakes")
    link_rail(nodes, "land_usa_upper_midwest", "land_usa_midwest")
    link_rail(nodes, "land_usa_midwest", "land_usa_great_lakes")
    link_rail(nodes, "land_usa_midwest", "land_usa_heartlands")
    link_rail(nodes, "land_usa_heartlands", "land_usa_appalachia")
    link_rail(nodes, "land_usa_heartlands", "land_usa_texas")
    link_rail(nodes, "land_usa_heartlands", "land_usa_new_orleans")
    link_rail(nodes, "land_usa_great_lakes", "land_usa_chicago")
    link_rail(nodes, "land_usa_chicago", "land_usa_heartlands")
    link_rail(nodes, "land_usa_chicago", "land_usa_appalachia")
    link_rail(nodes, "land_usa_the_northeast", "land_usa_appalachia")
    link_rail(nodes, "land_usa_the_northeast", "land_usa_new_york")
    link_rail(nodes, "land_usa_the_northeast", "land_usa_washington_dc")
    link_rail(nodes, "land_usa_appalachia", "land_usa_washington_dc")
    link_rail(nodes, "land_usa_appalachia", "land_usa_the_carolinas")
    link_rail(nodes, "land_usa_the_carolinas", "land_usa_southeastern_united_states")
    link_rail(nodes, "land_usa_southeastern_united_states", "land_usa_new_orleans")
    link_rail(nodes, "land_usa_new_orleans", "land_usa_texas")
    link_rail(nodes, "land_usa_southwest_united_states", "land_usa_texas")
    link_rail(nodes, "land_usa_southwest_united_states", "land_mex_western_mexico")
    link_rail(nodes, "land_usa_southwest_united_states", "land_usa_san_francisco")
    link_rail(nodes, "land_usa_san_francisco", "land_usa_western_united_states")
    link_rail(nodes, "land_usa_great_plains", "land_usa_upper_midwest")
    link_rail(nodes, "land_usa_great_plains", "land_usa_western_united_states")
    link_rail(nodes, "land_usa_great_plains", "land_usa_texas")
    link_rail(nodes, "land_usa_new_york", "land_usa_washington_dc")
    link_rail(nodes, "land_usa_new_york", "land_usa_chicago")
    link_rail(nodes, "land_usa_washington_dc", "land_usa_the_carolinas")

    link_rail(nodes, "land_mex_western_mexico", "land_mex_eastern_mexico")
    link_rail(nodes, "land_mex_eastern_mexico", "land_usa_texas")
    link_rail(nodes, "land_mex_eastern_mexico", "land_central_america")
    link_rail(nodes, "land_central_america", "land_panama")
    link_rail(nodes, "land_cuba", "land_hispaniola")

    # South America
    link_rail(nodes, "land_colombia", "land_venezuela")
    link_rail(nodes, "land_colombia", "land_ecuador")
    link_rail(nodes, "land_colombia", "land_peru")
    link_rail(nodes, "land_colombia", "land_panama")
    link_rail(nodes, "land_venezuela", "land_guyana")
    link_rail(nodes, "land_guyana", "land_suriname")
    link_rail(nodes, "land_suriname", "land_french_guiana")
    link_rail(nodes, "land_venezuela", "land_brazil_amazon_jungle")
    link_rail(nodes, "land_ecuador", "land_peru")
    link_rail(nodes, "land_peru", "land_bolivia", border_terrain="mountain")
    link_rail(nodes, "land_peru", "land_brazil_amazon_jungle")
    link_rail(nodes, "land_bolivia", "land_paraguay")
    link_rail(nodes, "land_bolivia", "land_chile", border_terrain="mountain")
    link_rail(nodes, "land_bolivia", "land_brazil_pampas")
    link_rail(nodes, "land_paraguay", "land_brazil_pampas")
    link_rail(nodes, "land_paraguay", "land_buenos_aires")
    link_rail(nodes, "land_paraguay", "land_rio_grande")
    link_rail(nodes, "land_brazil_amazon_jungle", "land_brazil_caatinga", border_terrain="jungle")
    link_rail(nodes, "land_brazil_caatinga", "land_brazil_rio_de_janeiro")
    link_rail(nodes, "land_brazil_rio_de_janeiro", "land_brazil_pampas")
    link_rail(nodes, "land_brazil_pampas", "land_rio_grande")
    link_rail(nodes, "land_brazil_pampas", "land_uruguay")
    link_rail(nodes, "land_uruguay", "land_buenos_aires")
    link_rail(nodes, "land_buenos_aires", "land_rio_grande")
    link_rail(nodes, "land_buenos_aires", "land_patagonia")
    link_rail(nodes, "land_patagonia", "land_chile")
    link_rail(nodes, "land_chile", "land_peru", border_terrain="mountain")
    link_rail(nodes, "land_chile", "land_bolivia", border_terrain="mountain")

    # Africa
    link_rail(nodes, "land_french_morocco", "land_spanish_morocco", border_terrain="mountain")
    link_rail(nodes, "land_french_morocco", "land_northern_algeria", border_terrain="mountain")
    link_rail(nodes, "land_northern_algeria", "land_western_algeria")
    link_rail(nodes, "land_northern_algeria", "land_southern_algeria")
    link_rail(nodes, "land_western_algeria", "land_southern_algeria")
    link_rail(nodes, "land_northern_algeria", "land_tunisia")
    link_rail(nodes, "land_tunisia", "land_tripoli")
    link_rail(nodes, "land_tripoli", "land_tripolitania")
    link_rail(nodes, "land_tripolitania", "land_cyrenaica")
    link_rail(nodes, "land_cyrenaica", "land_tobruk")
    link_rail(nodes, "land_tobruk", "land_western_egypt")
    link_rail(nodes, "land_western_egypt", "land_lower_egypt")
    link_rail(nodes, "land_lower_egypt", "land_upper_egypt")
    link_rail(nodes, "land_upper_egypt", "land_nubia")
    link_rail(nodes, "land_nubia", "land_sudan")
    link_rail(nodes, "land_sudan", "land_eritrea")
    link_rail(nodes, "land_eritrea", "land_abyssinia", border_terrain="mountain")
    link_rail(nodes, "land_abyssinia", "land_french_somaliland", border_terrain="mountain")
    link_rail(nodes, "land_abyssinia", "land_british_somaliland")
    link_rail(nodes, "land_abyssinia", "land_italian_somaliland")
    link_rail(nodes, "land_sudan", "land_abyssinia")

    link_rail(nodes, "land_french_sudan", "land_niger")
    link_rail(nodes, "land_niger", "land_chad")
    link_rail(nodes, "land_chad", "land_sudan")
    link_rail(nodes, "land_niger", "land_nigeria")
    link_rail(nodes, "land_dahomey", "land_nigeria")
    link_rail(nodes, "land_nigeria", "land_cameroon")
    link_rail(nodes, "land_cameroon", "land_oubangui_chari")
    link_rail(nodes, "land_oubangui_chari", "land_chad")
    link_rail(nodes, "land_oubangui_chari", "land_sudan")
    link_rail(nodes, "land_cameroon", "land_belgian_congo", border_terrain="jungle")
    link_rail(nodes, "land_belgian_congo", "land_oubangui_chari", border_terrain="jungle")
    link_rail(nodes, "land_belgian_congo", "land_angola")
    link_rail(nodes, "land_belgian_congo", "land_tanganyika")
    link_rail(nodes, "land_belgian_congo", "land_rhodesia")
    link_rail(nodes, "land_angola", "land_rhodesia")
    link_rail(nodes, "land_angola", "land_southwest_africa")
    link_rail(nodes, "land_rhodesia", "land_tanganyika")
    link_rail(nodes, "land_rhodesia", "land_portuguese_east_africa")
    link_rail(nodes, "land_rhodesia", "land_bechuanaland")
    link_rail(nodes, "land_rhodesia", "land_south_africa")
    link_rail(nodes, "land_southwest_africa", "land_bechuanaland")
    link_rail(nodes, "land_bechuanaland", "land_cape_town")
    link_rail(nodes, "land_bechuanaland", "land_south_africa")
    link_rail(nodes, "land_south_africa", "land_cape_town")
    link_rail(nodes, "land_tanganyika", "land_portuguese_east_africa")

    # East Asia + Oceania
    link_rail(nodes, "land_usr_stalino", "land_usr_vanavara")
    link_rail(nodes, "land_usr_vanavara", "land_usr_irkutsk")
    link_rail(nodes, "land_usr_irkutsk", "land_usr_angara")
    link_rail(nodes, "land_usr_irkutsk", "land_usr_buryatia")
    link_rail(nodes, "land_usr_angara", "land_usr_buryatia")
    link_rail(nodes, "land_usr_angara", "land_usr_chita")
    link_rail(nodes, "land_usr_chita", "land_usr_amur")
    link_rail(nodes, "land_usr_chita", "land_usr_buryatia")
    link_rail(nodes, "land_usr_amur", "land_usr_primorsky_krai")
    link_rail(nodes, "land_usr_amur", "land_usr_yakutsk")
    link_rail(nodes, "land_usr_yakutsk", "land_usr_southern_yakutia")
    link_rail(nodes, "land_usr_yakutsk", "land_usr_magadan")
    link_rail(nodes, "land_usr_magadan", "land_usr_kamchatka")
    link_rail(nodes, "land_usr_primorsky_krai", "land_usr_buryatia")
    link_rail(nodes, "land_usr_primorsky_krai", "land_manchuria_eastern")
    link_rail(nodes, "land_usr_north_sakhalin", "land_usr_south_sakhalin")

    link_rail(nodes, "land_mongolia_tannu_tuva", "land_mongolia_kobdo", border_terrain="mountain")
    link_rail(nodes, "land_mongolia_kobdo", "land_mongolia_ulyassutai")
    link_rail(nodes, "land_mongolia_ulyassutai", "land_mongolia_central_mongolia")
    link_rail(nodes, "land_mongolia_central_mongolia", "land_mongolia_kherlen")
    link_rail(nodes, "land_mongolia_kherlen", "land_manchuria_western")
    link_rail(nodes, "land_mongolia_central_mongolia", "land_manchuria_western")

    link_rail(nodes, "land_manchuria_northern", "land_manchuria_western")
    link_rail(nodes, "land_manchuria_western", "land_manchuria_eastern")
    link_rail(nodes, "land_manchuria_western", "land_manchuria_rehe")
    link_rail(nodes, "land_manchuria_rehe", "land_china_suiyuan")
    link_rail(nodes, "land_manchuria_rehe", "land_china_hopeh")
    link_rail(nodes, "land_manchuria_eastern", "land_korea", border_terrain="mountain", has_river=False)
    link_land(nodes, "land_korea", "land_usr_primorsky_krai", border_terrain="mountain", has_river=False)
    link_rail(nodes, "land_korea", "land_manchuria_rehe", border_terrain="mountain")
    link_rail(nodes, "land_manchuria_western", "land_usr_chita")
    link_rail(nodes, "land_manchuria_northern", "land_usr_amur")

    link_rail(nodes, "land_china_suiyuan", "land_china_hopeh")
    link_rail(nodes, "land_china_hopeh", "land_china_beiping")
    link_rail(nodes, "land_china_beiping", "land_china_shantung")
    link_rail(nodes, "land_china_shantung", "land_china_nanking")
    link_rail(nodes, "land_china_nanking", "land_china_hunan")
    link_rail(nodes, "land_china_hunan", "land_kwangtung")
    link_rail(nodes, "land_kwangtung", "land_kwangsi")
    link_rail(nodes, "land_kwangsi", "land_china_yunnan", border_terrain="mountain")
    link_rail(nodes, "land_china_yunnan", "land_china_kweichow", border_terrain="mountain")
    link_rail(nodes, "land_china_kweichow", "land_china_szechwan", border_terrain="mountain")
    link_rail(nodes, "land_china_szechwan", "land_china_shensi")
    link_rail(nodes, "land_china_shensi", "land_china_suiyuan")
    link_rail(nodes, "land_china_tsinghai", "land_china_szechwan", border_terrain="mountain")
    link_rail(nodes, "land_china_tsinghai", "land_china_sinkiang", border_terrain="mountain")
    link_rail(nodes, "land_china_sinkiang", "land_china_szechwan", border_terrain="mountain")
    link_rail(nodes, "land_china_shensi", "land_china_hunan")
    link_rail(nodes, "land_china_hunan", "land_china_kweichow")
    link_rail(nodes, "land_china_nanking", "land_china_hunan")
    link_rail(nodes, "land_kwangtung", "land_hong_kong")
    link_rail(nodes, "land_hong_kong", "land_kwangsi")
    link_rail(nodes, "land_annam_tonkin", "land_kwangsi", border_terrain="jungle")
    link_rail(nodes, "land_annam_tonkin", "land_cochinchina", border_terrain="jungle")
    link_rail(nodes, "land_cochinchina", "land_siam", border_terrain="jungle")
    link_rail(nodes, "land_siam", "land_kwangsi", border_terrain="jungle")
    link_rail(nodes, "land_siam", "land_burma", border_terrain="jungle")

    link_rail(nodes, "land_jap_honshu", "land_jap_kyushu")
    link_rail(nodes, "land_jap_honshu", "land_jap_hokkaido")

    link_rail(nodes, "land_luzon_and_the_visayas", "land_mindanao")
    link_rail(nodes, "land_sumatra", "land_java")
    link_rail(nodes, "land_java", "land_borneo")
    link_rail(nodes, "land_borneo", "land_celebes")
    link_rail(nodes, "land_timor", "land_aus_northern_territory")
    link_rail(nodes, "land_dutch_new_guinea", "land_new_guinea")
    link_rail(nodes, "land_new_guinea", "land_new_britain")

    link_rail(nodes, "land_aus_western_australia", "land_aus_northern_territory")
    link_rail(nodes, "land_aus_western_australia", "land_aus_south_australia")
    link_rail(nodes, "land_aus_south_australia", "land_aus_northern_territory")
    link_rail(nodes, "land_aus_south_australia", "land_aus_queensland")
    link_rail(nodes, "land_aus_south_australia", "land_aus_new_south_wales")
    link_rail(nodes, "land_aus_queensland", "land_aus_new_south_wales")
    link_rail(nodes, "land_aus_new_south_wales", "land_aus_tasmania")
    link_rail(nodes, "land_nz_north_island", "land_nz_south_island")

    # USSR west mesh
    link_rail(nodes, "land_usr_kola", "land_usr_karelia")
    link_rail(nodes, "land_usr_kola", "land_usr_northern_russia")
    link_rail(nodes, "land_usr_karelia", "land_usr_northern_russia")
    link_rail(nodes, "land_usr_karelia", "land_usr_leningrad")
    link_rail(nodes, "land_usr_northern_russia", "land_usr_yaroslavl")
    link_rail(nodes, "land_usr_northern_russia", "land_usr_western_russia")

    link_rail(nodes, "land_usr_leningrad", "land_usr_western_russia")
    link_rail(nodes, "land_usr_leningrad", "land_usr_northern_belorussia")
    link_rail(nodes, "land_usr_leningrad", "land_estonia")

    link_rail(nodes, "land_usr_western_russia", "land_usr_yaroslavl")
    link_rail(nodes, "land_usr_western_russia", "land_usr_smolensk")
    link_rail(nodes, "land_usr_western_russia", "land_usr_northern_belorussia")
    link_rail(nodes, "land_usr_western_russia", "land_usr_kaluga_oblast")
    link_rail(nodes, "land_usr_western_russia", "land_usr_moscow")

    link_rail(nodes, "land_usr_moscow", "land_usr_smolensk")
    link_rail(nodes, "land_usr_moscow", "land_usr_kaluga_oblast")
    link_rail(nodes, "land_usr_moscow", "land_usr_tula_lipetsk")
    link_rail(nodes, "land_usr_moscow", "land_usr_orel_kursk")
    link_rail(nodes, "land_usr_moscow", "land_usr_yaroslavl")

    link_rail(nodes, "land_usr_yaroslavl", "land_usr_gorky")
    link_rail(nodes, "land_usr_yaroslavl", "land_usr_moscow")

    link_rail(nodes, "land_usr_smolensk", "land_usr_northern_belorussia")
    link_rail(nodes, "land_usr_smolensk", "land_usr_southern_belorussia")
    link_rail(nodes, "land_usr_smolensk", "land_usr_kaluga_oblast")

    link_rail(nodes, "land_usr_northern_belorussia", "land_usr_southern_belorussia")
    link_rail(nodes, "land_usr_northern_belorussia", "land_latvia")

    link_rail(nodes, "land_usr_southern_belorussia", "land_usr_western_ukraine")
    link_rail(nodes, "land_usr_southern_belorussia", "land_usr_kiev")

    link_rail(nodes, "land_usr_western_ukraine", "land_usr_kiev")
    link_rail(nodes, "land_usr_western_ukraine", "land_usr_southern_ukraine")

    link_rail(nodes, "land_usr_kiev", "land_usr_eastern_ukraine", has_river=True)
    link_rail(nodes, "land_usr_kiev", "land_usr_southern_ukraine", has_river=True)
    link_rail(nodes, "land_usr_kiev", "land_usr_taurida", has_river=True)
    link_rail(nodes, "land_usr_kiev", "land_usr_orel_kursk")

    link_rail(nodes, "land_usr_eastern_ukraine", "land_usr_southern_ukraine")
    link_rail(nodes, "land_usr_eastern_ukraine", "land_usr_taurida")
    link_rail(nodes, "land_usr_eastern_ukraine", "land_usr_donets_kuban")
    link_rail(nodes, "land_usr_eastern_ukraine", "land_usr_orel_kursk")
    link_rail(nodes, "land_usr_eastern_ukraine", "land_usr_tula_lipetsk")

    link_rail(nodes, "land_usr_southern_ukraine", "land_usr_taurida")
    link_rail(nodes, "land_usr_southern_ukraine", "land_usr_crimea")

    link_rail(nodes, "land_usr_taurida", "land_usr_crimea")
    link_rail(nodes, "land_usr_taurida", "land_usr_donets_kuban")

    link_rail(nodes, "land_usr_crimea", "land_usr_donets_kuban")

    link_rail(nodes, "land_usr_donets_kuban", "land_usr_stalingrad")
    link_rail(nodes, "land_usr_donets_kuban", "land_usr_kalmytskaya")
    link_rail(nodes, "land_usr_donets_kuban", "land_usr_north_caucasia")

    link_rail(nodes, "land_usr_stalingrad", "land_usr_kalmytskaya")
    link_rail(nodes, "land_usr_stalingrad", "land_usr_tula_lipetsk")
    link_rail(nodes, "land_usr_stalingrad", "land_usr_saratov")
    link_rail(nodes, "land_usr_stalingrad", "land_usr_north_caucasia")

    link_rail(nodes, "land_usr_kalmytskaya", "land_usr_saratov")
    link_rail(nodes, "land_usr_kalmytskaya", "land_usr_north_caucasia")

    link_rail(nodes, "land_usr_north_caucasia", "land_usr_transcaucasia", border_terrain="mountain")
    link_rail(nodes, "land_usr_tula_lipetsk", "land_usr_orel_kursk")
    link_rail(nodes, "land_usr_tula_lipetsk", "land_usr_saratov")
    link_rail(nodes, "land_usr_gorky", "land_usr_tula_lipetsk")
    link_rail(nodes, "land_usr_gorky", "land_usr_saratov")

    # UK rail mesh
    link_rail(nodes, "land_gbr_scotland", "land_gbr_northern_england")
    link_rail(nodes, "land_gbr_northern_england", "land_gbr_southern_england")
    link_rail(nodes, "land_gbr_southern_england", "land_gbr_london")
    link_rail(nodes, "land_gbr_northern_england", "land_gbr_london")

    # Land-sea coast links with ports/docks where visible
    for lid in ["land_gbr_scotland", "land_nor_trondelag", "land_nor_southern_norway"]:
        link_land_sea(nodes, lid, "sea_a6", port=True)
    for lid in ["land_gbr_scotland", "land_nor_southern_norway", "land_denmark"]:
        link_land_sea(nodes, lid, "sea_a10", port=True)

    for lid in ["land_denmark", "land_ger_western_germany", "land_neu_netherlands", "land_neu_belgium", "land_gbr_southern_england", "land_gbr_london"]:
        link_land_sea(nodes, lid, "sea_a23", port=True)

    for lid in ["land_gbr_southern_england", "land_gbr_northern_england", "land_ireland"]:
        link_land_sea(nodes, lid, "sea_a21", port=True)

    for lid in ["land_ireland", "land_fra_normandy", "land_fra_picardy"]:
        link_land_sea(nodes, lid, "sea_a22", port=(lid != "land_fra_normandy"))

    for lid in ["land_denmark", "land_swe_gotland", "land_ger_konigsberg", "land_ger_eastern_germany", "land_estonia", "land_usr_leningrad"]:
        link_land_sea(nodes, lid, "sea_a12", port=True)

    for lid in ["land_fin_southern_finland", "land_swe_gotland", "land_estonia", "land_usr_kola"]:
        link_land_sea(nodes, lid, "sea_a13", port=True)

    for lid in ["land_fin_lapland", "land_swe_norrland", "land_usr_kola"]:
        link_land_sea(nodes, lid, "sea_a14", port=False)

    for lid in ["land_fra_aquitaine", "land_esp_basque_country", "land_esp_catalonia", "land_fra_southern_france"]:
        link_land_sea(nodes, lid, "sea_a28", port=True)

    link_land_sea(nodes, "land_fra_southern_france", "sea_m1", port=True)
    link_land_sea(nodes, "land_fra_corsica", "sea_m3", port=True)
    link_land_sea(nodes, "land_ita_sardinia", "sea_m3", port=True)
    link_land_sea(nodes, "land_ita_northern_italy", "sea_m3", port=True)
    link_land_sea(nodes, "land_ita_rome", "sea_m3", port=True)
    link_land_sea(nodes, "land_ita_lazio", "sea_m4", port=True)
    link_land_sea(nodes, "land_ita_southern_italy", "sea_m4", port=True)
    link_land_sea(nodes, "land_ita_southern_italy", "sea_m5", port=True)
    link_land_sea(nodes, "land_yug_western_yugoslavia", "sea_m5", port=True)
    link_land_sea(nodes, "land_albania", "sea_m5", port=True)
    link_land_sea(nodes, "land_gre_macedonia", "sea_m5", port=True)

    link_land_sea(nodes, "land_bulgaria", "sea_m10", port=True)
    link_land_sea(nodes, "land_rom_bessarabia", "sea_m10", port=True)
    link_land_sea(nodes, "land_usr_crimea", "sea_m10", port=True)
    link_land_sea(nodes, "land_tur_istanbul", "sea_m10", port=True, canal="Turkish Straits")

    link_land_sea(nodes, "land_tur_karadeniz", "sea_m11", port=True)
    link_land_sea(nodes, "land_tur_akdeniz", "sea_m11", port=False)
    link_land_sea(nodes, "land_usr_taurida", "sea_m11", port=True)
    link_land_sea(nodes, "land_usr_crimea", "sea_m11", port=True)
    link_land_sea(nodes, "land_usr_north_caucasia", "sea_m11", port=True)
    link_land_sea(nodes, "land_usr_transcaucasia", "sea_m11", port=True)

    link_land_sea(nodes, "land_usr_transcaucasia", "sea_m12", port=False)
    link_land_sea(nodes, "land_azerbaijan", "sea_m12", port=False)

    link_land_sea(nodes, "land_syria", "sea_m9", port=True)
    link_land_sea(nodes, "land_transjordan", "sea_m9", port=True)
    link_land_sea(nodes, "land_southern_iraq", "sea_i7", port=True)
    link_land_sea(nodes, "land_kuwait", "sea_i7", port=True)
    link_land_sea(nodes, "land_iran_southern_iran", "sea_i7", port=True)
    link_land_sea(nodes, "land_iran_southern_iran", "sea_i6", port=True)
    link_land_sea(nodes, "land_saudi_arabia", "sea_i3", port=False)
    link_land_sea(nodes, "land_saudi_arabia", "sea_i6", port=False)
    link_land_sea(nodes, "land_qatar", "sea_i7", port=True)
    link_land_sea(nodes, "land_oman", "sea_i6", port=True)
    link_land_sea(nodes, "land_aden", "sea_i3", port=True)
    link_rail(nodes, "land_saudi_arabia", "land_oman", border_terrain="desert")
    link_rail(nodes, "land_saudi_arabia", "land_aden", border_terrain="desert")
    link_rail(nodes, "land_saudi_arabia", "land_qatar", border_terrain="desert")
    link_rail(nodes, "land_qatar", "land_oman", border_terrain="desert")

    link_land_sea(nodes, "land_india_maharashtra", "sea_i6", port=True)
    link_land_sea(nodes, "land_india_southern_india", "sea_i6", port=True)
    link_land_sea(nodes, "land_india_southern_india", "sea_i11", port=True)
    link_land_sea(nodes, "land_india_calcutta", "sea_i11", port=True)
    link_land_sea(nodes, "land_india_ceylon", "sea_i6", port=True)
    link_land_sea(nodes, "land_india_ceylon", "sea_i11", port=True)
    link_land_sea(nodes, "land_burma", "sea_i11", port=True)
    link_rail(nodes, "land_india_southern_india", "land_india_ceylon")

    # Americas coast/port links
    link_land_sea(nodes, "land_can_district_of_keewatin", "sea_a1", port=False)
    link_land_sea(nodes, "land_can_baffin_island", "sea_a1", port=False)
    link_land_sea(nodes, "land_can_baffin_island", "sea_a2", port=False)
    link_land_sea(nodes, "land_can_labrador", "sea_a15", port=True)
    link_land_sea(nodes, "land_can_labrador", "sea_a18", port=True)
    link_land_sea(nodes, "land_can_ontario", "sea_a24", port=True)
    link_land_sea(nodes, "land_usa_great_lakes", "sea_a24", port=True)
    link_land_sea(nodes, "land_can_newfoundland", "sea_a18", port=True)
    link_land_sea(nodes, "land_can_nova_scotia", "sea_a18", port=True)
    link_land_sea(nodes, "land_can_st_pierre_island", "sea_a18", port=True)
    link_land_sea(nodes, "land_can_quebec", "sea_a15", port=True)
    link_land_sea(nodes, "land_can_manitoba", "sea_a1", port=False)
    link_land_sea(nodes, "land_can_british_columbia", "sea_p5", port=True)
    link_land_sea(nodes, "land_can_british_columbia", "sea_p6", port=True)

    link_land_sea(nodes, "land_usa_pacific_northwest", "sea_p6", port=True)
    link_land_sea(nodes, "land_usa_western_united_states", "sea_p25", port=False)
    link_land_sea(nodes, "land_usa_san_francisco", "sea_p28", port=True)
    link_land_sea(nodes, "land_usa_southwest_united_states", "sea_p30", port=True)
    link_land_sea(nodes, "land_mex_western_mexico", "sea_p30", port=True)
    link_land_sea(nodes, "land_mex_western_mexico", "sea_p31", port=True)

    link_land_sea(nodes, "land_usa_new_york", "sea_a25", port=True)
    link_land_sea(nodes, "land_usa_washington_dc", "sea_a26", port=True)
    link_land_sea(nodes, "land_usa_the_carolinas", "sea_a26", port=True)
    link_land_sea(nodes, "land_usa_southeastern_united_states", "sea_a31", port=True)
    link_land_sea(nodes, "land_usa_new_orleans", "sea_a36", port=True)
    link_land_sea(nodes, "land_bermuda", "sea_a31", port=True)
    link_land_sea(nodes, "land_cuba", "sea_a36", port=True)
    link_land_sea(nodes, "land_hispaniola", "sea_a36", port=True)
    link_land_sea(nodes, "land_puerto_rico", "sea_a36", port=True)
    link_land_sea(nodes, "land_panama", "sea_a36", port=True)
    link_land_sea(nodes, "land_panama", "sea_p31", port=True, canal="Panama Canal")
    link(nodes, "sea_a36", "sea_p31", border_terrain="sea", connecting_terrain="sea", canal_or_strait="Panama Canal", inference_confidence=0.9)

    link_land_sea(nodes, "land_colombia", "sea_a36", port=True)
    link_land_sea(nodes, "land_venezuela", "sea_a36", port=True)
    link_land_sea(nodes, "land_guyana", "sea_a38", port=True)
    link_land_sea(nodes, "land_suriname", "sea_a38", port=True)
    link_land_sea(nodes, "land_french_guiana", "sea_a38", port=True)
    link_land_sea(nodes, "land_brazil_caatinga", "sea_a38", port=True)
    link_land_sea(nodes, "land_brazil_rio_de_janeiro", "sea_a39", port=True)
    link_land_sea(nodes, "land_brazil_pampas", "sea_a39", port=True)
    link_land_sea(nodes, "land_uruguay", "sea_a39", port=True)
    link_land_sea(nodes, "land_buenos_aires", "sea_a40", port=True)
    link_land_sea(nodes, "land_patagonia", "sea_a40", port=True)
    link_land_sea(nodes, "land_chile", "sea_p31", port=True)

    # Africa coast/port links
    link_land_sea(nodes, "land_french_morocco", "sea_a28", port=True)
    link_land_sea(nodes, "land_spanish_morocco", "sea_a28", port=True)
    link_land_sea(nodes, "land_northern_algeria", "sea_m1", port=True)
    link_land_sea(nodes, "land_tunisia", "sea_m1", port=True)
    link_land_sea(nodes, "land_tripoli", "sea_m1", port=True)
    link_land_sea(nodes, "land_tobruk", "sea_m9", port=True)
    link_land_sea(nodes, "land_western_egypt", "sea_m9", port=True)
    link_land_sea(nodes, "land_lower_egypt", "sea_m9", port=True)
    link_land_sea(nodes, "land_upper_egypt", "sea_i5", port=True, canal="Suez Canal")
    link_land_sea(nodes, "land_lower_egypt", "sea_i5", port=True, canal="Suez Canal")
    link(nodes, "sea_m9", "sea_i5", border_terrain="sea", connecting_terrain="sea", canal_or_strait="Suez Canal", inference_confidence=0.94)

    link_land_sea(nodes, "land_eritrea", "sea_i5", port=True)
    link_land_sea(nodes, "land_french_somaliland", "sea_i5", port=True)
    link_land_sea(nodes, "land_british_somaliland", "sea_i4", port=True)
    link_land_sea(nodes, "land_italian_somaliland", "sea_i4", port=True)
    link_land_sea(nodes, "land_tanganyika", "sea_i4", port=True)
    link_land_sea(nodes, "land_portuguese_east_africa", "sea_i4", port=True)
    link_land_sea(nodes, "land_madagascar", "sea_i4", port=True)
    link_land_sea(nodes, "land_mauritius", "sea_i4", port=True)
    link_land_sea(nodes, "land_seychelles", "sea_i4", port=True)

    link_land_sea(nodes, "land_dahomey", "sea_a38", port=True)
    link_land_sea(nodes, "land_nigeria", "sea_a38", port=True)
    link_land_sea(nodes, "land_cameroon", "sea_a38", port=True)
    link_land_sea(nodes, "land_angola", "sea_a39", port=True)
    link_land_sea(nodes, "land_southwest_africa", "sea_a39", port=True)
    link_land_sea(nodes, "land_cape_town", "sea_a40", port=True)
    link_land_sea(nodes, "land_south_africa", "sea_a40", port=True)

    # East Asia + Oceania coast/port links
    link_land_sea(nodes, "land_usr_kamchatka", "sea_p2", port=False)
    link_land_sea(nodes, "land_usr_magadan", "sea_p2", port=False)
    link_land_sea(nodes, "land_usr_north_sakhalin", "sea_p2", port=False)
    link_land_sea(nodes, "land_usr_south_sakhalin", "sea_p8", port=True)
    link_land_sea(nodes, "land_usr_primorsky_krai", "sea_p7", port=True)
    link_land_sea(nodes, "land_jap_hokkaido", "sea_p8", port=True)
    link_land_sea(nodes, "land_jap_hokkaido", "sea_p7", port=True)
    link_land_sea(nodes, "land_jap_honshu", "sea_p7", port=True)
    link_land_sea(nodes, "land_jap_honshu", "sea_p15", port=True)
    link_land_sea(nodes, "land_jap_kyushu", "sea_p15", port=True)
    link_land_sea(nodes, "land_korea", "sea_p15", port=True)
    link_land_sea(nodes, "land_korea", "sea_p14", port=True)
    link_land_sea(nodes, "land_manchuria_eastern", "sea_p7", port=True)
    link_land_sea(nodes, "land_china_shantung", "sea_p14", port=True)
    link_land_sea(nodes, "land_china_nanking", "sea_p15", port=True)
    link_land_sea(nodes, "land_formosa", "sea_p15", port=True)
    link_land_sea(nodes, "land_hainan", "sea_p50", port=True)
    link_land_sea(nodes, "land_hong_kong", "sea_p50", port=True)
    link_land_sea(nodes, "land_kwangtung", "sea_p50", port=True)
    link_land_sea(nodes, "land_annam_tonkin", "sea_p50", port=True)
    link_land_sea(nodes, "land_cochinchina", "sea_p50", port=True)
    link_land_sea(nodes, "land_siam", "sea_p50", port=True)
    link_land_sea(nodes, "land_luzon_and_the_visayas", "sea_p32", port=True)
    link_land_sea(nodes, "land_mindanao", "sea_p52", port=True)
    link_land_sea(nodes, "land_palau", "sea_p34", port=True)
    link_land_sea(nodes, "land_guam", "sea_p34", port=True)
    link_land_sea(nodes, "land_sumatra", "sea_p59", port=True)
    link_land_sea(nodes, "land_java", "sea_p59", port=True)
    link_land_sea(nodes, "land_borneo", "sea_p59", port=True)
    link_land_sea(nodes, "land_celebes", "sea_p60", port=True)
    link_land_sea(nodes, "land_timor", "sea_p61", port=True)
    link_land_sea(nodes, "land_dutch_new_guinea", "sea_p61", port=True)
    link_land_sea(nodes, "land_new_guinea", "sea_p63", port=True)
    link_land_sea(nodes, "land_new_britain", "sea_p63", port=True)
    link_land_sea(nodes, "land_aus_western_australia", "sea_i6", port=True)
    link_land_sea(nodes, "land_aus_northern_territory", "sea_p61", port=True)
    link_land_sea(nodes, "land_aus_queensland", "sea_p62", port=True)
    link_land_sea(nodes, "land_aus_new_south_wales", "sea_p68", port=True)
    link_land_sea(nodes, "land_aus_tasmania", "sea_p68", port=True)
    link_land_sea(nodes, "land_nz_north_island", "sea_p69", port=True)
    link_land_sea(nodes, "land_nz_south_island", "sea_p69", port=True)
    link_land_sea(nodes, "land_new_caledonia", "sea_p65", port=True)
    link_land_sea(nodes, "land_fiji", "sea_p65", port=True)
    link_land_sea(nodes, "land_new_hebrides", "sea_p65", port=True)

    # Denmark straits and canal/strait annotations
    link(nodes, "sea_a10", "sea_a11", border_terrain="sea", connecting_terrain="sea", canal_or_strait="Danish Straits", inference_confidence=0.9)
    link(nodes, "sea_a11", "sea_a12", border_terrain="sea", connecting_terrain="sea", canal_or_strait="Danish Straits", inference_confidence=0.9)
    link(nodes, "land_denmark", "land_swe_gotland", border_terrain="coast", connecting_terrain="coast", narrow_crossing=True, canal_or_strait="Danish Straits", inference_confidence=0.84)

    # Turkish straits (treated as canal in rules)
    link(nodes, "sea_m10", "sea_m11", border_terrain="sea", connecting_terrain="sea", canal_or_strait="Turkish Straits", inference_confidence=0.95)

    # Kaiser-Wilhelm Canal note between North Sea and Baltic adjacency near Western Germany
    link(nodes, "sea_a23", "sea_a12", border_terrain="sea", connecting_terrain="sea", canal_or_strait="Kaiser-Wilhelm Kanal", inference_confidence=0.82)

    # Ports in Germany/France/UK linked on both relevant seas
    link_land_sea(nodes, "land_ger_western_germany", "sea_a12", port=True, canal="Kaiser-Wilhelm Kanal")
    link_land_sea(nodes, "land_fra_normandy", "sea_a23", port=True)
    link_land_sea(nodes, "land_fra_picardy", "sea_a23", port=True)

    # Clean neighbors: sort and dedupe per node
    for nid, node in nodes.items():
        seen = {}
        for e in node.get("neighbors", []):
            seen[e["neighbor_id"]] = e
        node["neighbors"] = [seen[k] for k in sorted(seen.keys())]

    # Ensure symmetric closure (best-effort defaults for missing reverse)
    for src, node in list(nodes.items()):
        for e in list(node.get("neighbors", [])):
            dst = e["neighbor_id"]
            if dst not in nodes:
                continue
            revs = [x for x in nodes[dst].get("neighbors", []) if x["neighbor_id"] == src]
            if not revs:
                set_edge(nodes, dst, src, **{k: v for k, v in e.items() if k != "neighbor_id"})

    # Deterministic node ordering
    doc["nodes"] = {k: nodes[k] for k in sorted(nodes.keys())}

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=True, indent=2)

    print(f"Wrote {OUTPUT} with {len(doc['nodes'])} nodes")


if __name__ == "__main__":
    build()
