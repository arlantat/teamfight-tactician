import json
import logging
import os
import random
import sqlite3
import time
from itertools import permutations
import requests

from utils import init_encoded_traits, server_to_region, CURRENT_VERSION, update_item_augment_map, MY_SERVER, MY_REGION, \
    get_trait_name, item_in_class


def main():
    con = sqlite3.connect("tft_stats.db")
    con.isolation_level = None
    cur = con.cursor()
    server = MY_SERVER
    region = MY_REGION

    server_to_matches(cur, server, region)
    update_meta(cur, server)

    # pool(cur, '', i_augments=['a portableforge'], i_units=[['u illaoi'], [2], [[]]], i_traits=[['t bruiser'], [1]])

    con.close()


logging.basicConfig(level=logging.INFO)

IGNOREDUNITS = []

TRAIT_TO_ENCODED, ENCODED_TO_TRAIT = init_encoded_traits()
RIOT_API = os.environ.get('RIOT_API')
update_item_augment_map()
with open('item_augment_map.json', 'r') as f:
    ITEM_AUGMENT_MAP = json.load(f)


def update_meta(cursor, server, fn=None):
    with open('meta.txt', 'w') as file:
        if fn is None or fn == 'check':
            check_db(cursor, file, server, CURRENT_VERSION)
        if fn is None or fn == 'best-items':
            update_best_items(file, cursor)
        if fn is None or fn == 'traits':
            avg(file, cursor, 'traits')
        if fn is None or fn == 'units':
            avg(file, cursor, 'units')
        if fn is None or fn == '3-star-units':
            avg(file, cursor, 'units', 'maxed')
        if fn is None or fn == 'items':
            avg(file, cursor, 'items')
        if fn is None or fn == 'augments':
            avg(file, cursor, 'augments')
        if fn is None or fn == 'comps':
            avg(file, cursor, 'comps')


def pool(cursor, file, i_augments=None, i_units=None, i_traits=None):
    """
        i_augments: a list of max length 3 of augments, unordered
        i_units: a 8x3 list, with the first being units, second being tiers, third being items in the form of lists
        i_traits: a 8x2 list, with the first being traits, the second being tiers.
        augment string: "a {augment_name}"
        unit string: "u {unit_name}"
        item string: "{ir OR ic OR ia OR is} {item_name}"
        trait string: "t {trait_name}"
        tier int: int from 0 to highest tier of the intended object
    """
    global trio
    if i_traits is None:
        i_traits = []
    if i_units is None:
        i_units = []
    if i_augments is None:
        i_augments = []
    inputs = [[i_augments, 'p', 'player_states', None, None, 'augment'],
              [i_units, 'u', 'unit_states', 'character_id', 'tier', 'item'],
              [i_traits, 't', 'trait_states', 'name', 'tier_current', None]
              ]
    subqueries = []
    for arg in inputs:
        if arg[0] != []:
            cur = arg[0]
            alias = arg[1]
            table = arg[2]
            primary = arg[3]
            secondary = arg[4]
            tertiary = arg[5]
            subquery = f"SELECT {alias}1.puuid, {alias}1.match_id FROM {table} {alias}1 "
            where_statement = "WHERE "
            wheres = []
            loops = 1
            if alias != 'p':
                loops = len(cur[0])
            for i in range(loops):
                if i != 0:  # inner joins start from u2
                    innerjoin = f"INNER JOIN {table} {alias}{i + 1} ON {alias}1.puuid = {alias}{i + 1}.puuid AND {alias}1.match_id = {alias}{i + 1}.match_id "
                    subquery += innerjoin
                if alias != 'p':  # primary, character_id and name
                    wheres.append(f"{alias}{i + 1}.{primary} = '{string_to_canon(cursor, cur[0][i])}'")
                if alias != 'p' and cur[1][i] != 0:  # secondary, tier and tier_current
                    wheres.append(f"{alias}{i + 1}.{secondary} = {cur[1][i]}")
                if (alias == 'u' and cur[2][i] != []) or (alias == 'p' and cur != []):  # tertiary, item and augment
                    if alias == 'p':
                        trio = list(map(lambda x: string_to_canon(cursor, x), cur))
                    elif alias == 'u':
                        trio = list(map(lambda x: string_to_canon(cursor, x), cur[2][i]))
                    inner_query = ""
                    if len(trio) == 1:
                        inner_query = f"{alias}{i + 1}.{tertiary}1 = '{trio[0]}' OR {alias}{i + 1}.{tertiary}2 = '{trio[0]}' OR {alias}{i + 1}.{tertiary}3 = '{trio[0]}'"
                    else:
                        all_items = []
                        if len(trio) == 2:
                            all_permutations = [(1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2)]
                            for x, y in all_permutations:
                                statement = f"({alias}{i + 1}.{tertiary}{x} = '{trio[0]}' AND {alias}{i + 1}.{tertiary}{y} = '{trio[1]}')"
                                all_items.append(statement)
                        elif len(trio) == 3:
                            all_permutations = list(permutations(trio))
                            for perm in all_permutations:
                                statement = f"({alias}{i + 1}.{tertiary}1 = '{perm[0]}' AND {alias}{i + 1}.{tertiary}2 = '{perm[1]}' AND {alias}{i + 1}.{tertiary}3 = '{perm[2]}')"
                                all_items.append(statement)
                        inner_query = " OR ".join(all_items)
                    wheres.append(f"({inner_query})")
            subquery = subquery + where_statement + " AND ".join(wheres)
            # print(subquery)
            subqueries.append([subquery, alias])
    if len(subqueries) == 1:
        cursor.execute(subqueries[0][0])
        print(subqueries[0][0])
    else:
        main_query = f"SELECT {subqueries[0][1]}.puuid, {subqueries[0][1]}.match_id FROM ({subqueries[0][0]}) AS {subqueries[0][1]}"
        for subquery, alias in subqueries[1:]:
            main_query += f" JOIN ({subquery}) AS {alias} ON {subqueries[0][1]}.puuid = {alias}.puuid AND {subqueries[0][1]}.match_id = {alias}.match_id"
        cursor.execute(main_query)
        print(main_query)

    rs = cursor.fetchall()
    if not rs:
        print('no records found')
        return
    placeholders = ','.join(['(?,?)' for _ in range(len(rs))])
    query = f'''
        SELECT AVG(placement) AS average_placement
        FROM player_states
        WHERE (puuid, match_id) IN ({placeholders})
    '''
    flat_pairs = [item for sublist in rs for item in sublist]
    cursor.execute(query, flat_pairs)
    avg = cursor.fetchone()
    print(avg)
    return


def update_best_items(file, cursor):
    cursor.execute('''SELECT us.item1, us.item2, us.item3, ps.placement, us.tier, u.name 
                FROM unit_states us INNER JOIN player_states ps INNER JOIN units u
                ON us.match_id = ps.match_id AND us.puuid = ps.puuid AND us.apiName = u.apiName
        ''')
    rs = cursor.fetchall()
    unit_map = {}  # dictionary of unit: item_map
    for r in rs:
        items = r[:3]
        placement = r[3]
        tier = r[4]
        unit = r[5]
        if unit not in unit_map:
            unit_map[unit] = {}  # dictionary of item: [sum, cnt]
        for item in items:
            if item is not None:
                cursor.execute("SELECT class, name FROM items WHERE apiName = ?", (item,))
                item_class, item_name = cursor.fetchone()
                if item_class == 'ignored':
                    continue
                if item_name not in unit_map[unit]:
                    unit_map[unit][item_name] = [placement, 1]
                else:
                    unit_map[unit][item_name][0] += placement
                    unit_map[unit][item_name][1] += 1
    best_units = {}  # item: [cnt, avrg, unit]
    file.write('---------BEST ITEMS FOR EACH UNIT---------\n')
    for unit, item_map in unit_map.items():
        li = []
        for item_name, val in item_map.items():
            avrg = val[0] / val[1]
            li.append((val[1], avrg, item_name))
            if item_name not in best_units:
                best_units[item_name] = []
            best_units[item_name].append([val[1], avrg, unit])
        # first sort by matches
        li.sort(key=lambda s: s[0], reverse=True)

        # doesn't make sense to include support items here
        ornn = [s for s in li if item_in_class(cursor, s[2], 'ornn')]
        craftable = [s for s in li if item_in_class(cursor, s[2], 'craftable')]
        emblem = [s for s in li if item_in_class(cursor, s[2], 'emblem')]
        radiant = [s for s in li if item_in_class(cursor, s[2], 'radiant')]
        other = [s for s in li if item_in_class(cursor, s[2], 'other')]

        # now sort by avrg
        best_craftables = sorted(craftable[:15], key=lambda x: x[1])
        best_radiants = sorted(radiant[:3], key=lambda x: x[1])
        best_emblems = sorted(emblem[:3], key=lambda x: x[1])
        best_ornns = sorted(ornn[:3], key=lambda x: x[1])
        if unit == 'Kayle':
            best_others = sorted(other, key=lambda x: x[1])
        else:
            best_others = sorted(other[:3], key=lambda x: x[1])

        def write_best_items(file, unit, class_name, items):
            file.write(f"best {class_name} for {unit} are {[(s[2], round(s[1], 2), s[0]) for s in items]}\n")

        write_best_items(file, unit, 'craftables', best_craftables)
        write_best_items(file, unit, 'radiants', best_radiants)
        write_best_items(file, unit, 'emblems', best_emblems)
        write_best_items(file, unit, 'ornns', best_ornns)
        write_best_items(file, unit, 'others', best_others)
        file.write('\n')

    # best units for each item, same process
    file.write('---------BEST UNITS FOR EACH ITEM---------\n')
    for item_name in best_units:
        best_units[item_name].sort(key=lambda s: s[0], reverse=True)
        li = sorted(best_units[item_name][:7], key=lambda s: s[1])
        file.write(f"best units for {item_name} are {[(s[2], round(s[1], 2), s[0]) for s in li]}\n")
    file.write('\n')


def avg(file, cursor, table, arg=None):
    """
    table = traits, units, items, augments, comps.
    if 'units' is passed, arg can be 'maxed'.
    if 'items' is passed, arg can be 'craftable', 'radiant', 'ornn', 'emblem', 'support', 'other'.
    if 'augments' is passed, arg can be '1', '2', '3'.
    """
    head = ('SELECT CAST(sum_placement AS REAL) / num_placement AS avg, CAST(top4 AS REAL) / num_placement AS '
            'top4_rate, num_placement')
    tail = "num_placement IS NOT NULL"
    if table == 'traits':
        cursor.execute(f"{head}, name FROM {table} WHERE {tail}")
    elif table == "comps":
        cursor.execute(f"{head}, encoded FROM {table} WHERE {tail} ORDER BY num_placement DESC LIMIT 50")
    elif table == 'items':
        if arg is None:
            avg(file, cursor, table, arg='craftable')
            avg(file, cursor, table, arg='radiant')
            avg(file, cursor, table, arg='ornn')
            avg(file, cursor, table, arg='emblem')
            avg(file, cursor, table, arg='support')
            avg(file, cursor, table, arg='other')
            return
        else:
            cursor.execute(f"{head}, name FROM {table} WHERE class = ? and {tail}", (arg,))
    elif table == 'augments':
        if arg is None:
            avg(file, cursor, table, arg='1')
            avg(file, cursor, table, arg='2')
            avg(file, cursor, table, arg='3')
            return
        else:
            cursor.execute(f"{head}, name FROM {table} WHERE stage = ? and {tail}", (arg,))
    elif table == 'units':
        if arg == 'maxed':
            cursor.execute(f"""SELECT CAST(u3.sum_placement AS REAL) / u3.num_placement AS avg, 
                CAST(u3.top4 AS REAL) / u3.num_placement AS top4_rate, 
                u3.num_placement, u.name FROM units_3 u3 INNER JOIN units u ON u3.apiName = u.apiName
                WHERE u3.num_placement IS NOT NULL""")
        else:
            cursor.execute(f"{head}, name FROM {table} WHERE {tail}")
    rows = cursor.fetchall()
    li = []
    for row in rows:
        avrg, top4_rate, num_placement, col1, col2 = row[0], row[1], row[2], row[3], None
        if len(row) == 5:
            col2 = row[4]
        if avrg is not None:
            li.append((avrg, top4_rate, num_placement, col1, col2))
    li.sort(key=lambda x: x[0])
    if arg in ['craftable', 'radiant', 'ornn', 'emblem', 'support', 'other']:
        file.write(f"---------{arg.upper()} ITEMS----------\n")
    elif arg in ['1', '2', '3']:
        file.write(f"---------AUGMENT {arg.upper()}----------\n")
    elif arg == 'maxed':
        file.write(f"---------3 STAR UNITS----------\n")
    else:
        file.write(f"--------------{table.upper()}---------------\n")
    for row in li:
        if table == 'traits':
            file.write(
                f"""average placement of {row[3]} is {row[0]:.2f}, top 4 rate {row[1] * 100:.2f}, {row[2]} spots\n""")
        elif table == 'comps':
            trait1, trait2, trait3 = '', '', ''
            if row[3] == 'bd':
                file.write(
                    f"average placement of Built Different is {row[0]:.2f}, top 4 rate {row[1] * 100:.2f}, {row[2]} spots\n")
                continue
            elif row[3] == 'lg':
                file.write(
                    f"average placement of Legendary Variants is {row[0]:.2f}, top 4 rate {row[1] * 100:.2f}, {row[2]} spots\n")
                continue
            trait1 = get_trait_name(cursor, ENCODED_TO_TRAIT[row[3][0]], int(row[3][1]))
            if len(row[3]) >= 4:
                trait2 = get_trait_name(cursor, ENCODED_TO_TRAIT[row[3][2]], int(row[3][3]))
            if len(row[3]) == 6:
                trait3 = get_trait_name(cursor, ENCODED_TO_TRAIT[row[3][4]], int(row[3][5]))
            file.write(f"average placement of {trait1}" +
                       (f", {trait2}" if trait2 else "") +
                       (f", {trait3}" if trait3 else "") +
                       f" is {row[0]:.2f}, top 4 rate {(row[1] * 100):.2f}, {row[2]} spots\n")
        elif table == 'units':
            file.write(
                f"average placement of {row[3]} is {row[0]:.2f}, top 4 rate {(row[1] * 100):.2f}, {row[2]} spots\n")
        else:
            file.write(
                f"average placement of {row[3]} is {row[0]:.2f}, top 4 rate {(row[1] * 100):.2f}, {row[2]} spots\n")
    file.write('\n')


def insert_match(cursor, server, region, match_id):
    if match_id == '' or match_id is None:
        return
    cursor.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,))
    if cursor.fetchone() is not None:
        return
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        if res.status_code == 403:
            print(match_id)
        # wait and retry if rate limit exceeded
        if res.status_code == 429:
            time.sleep(25)
            insert_match(cursor, server, region, match_id)
        return
    result = res.json()
    info = result['info']
    if info['game_version'].startswith(CURRENT_VERSION) and info['queue_id'] == 1100:
        cursor.execute("INSERT INTO matches (match_id) VALUES (?)", (match_id,))
        for participant in info['participants']:
            # augments
            augments = participant['augments']
            if len(augments) < 3:
                continue
            for i, api_name in enumerate(augments):
                name = ''
                if api_name in ITEM_AUGMENT_MAP:
                    name = ITEM_AUGMENT_MAP[api_name]
                cursor.execute('SELECT sum_placement FROM augments WHERE apiName = ? AND stage = ?', (api_name, i + 1))
                r = cursor.fetchone()
                if not r:
                    cursor.execute('''INSERT INTO augments (apiName, stage, name, sum_placement, num_placement, top4) 
                                    VALUES (?, ?, ?, ?, ?, ?)''', (
                        api_name, i + 1, name, participant['placement'], 1,
                        (1 if participant['placement'] <= 4 else 0)))
                elif r[0] is None:
                    cursor.execute('''UPDATE augments 
                                SET sum_placement = ?, num_placement = 1, top4 = ? WHERE apiName = ? AND stage = ?''', (
                        participant['placement'], (1 if participant['placement'] <= 4 else 0), api_name, i + 1))
                else:
                    cursor.execute('''UPDATE augments 
                    SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ?, name = ?
                    WHERE apiName = ? AND stage = ?''', (
                        participant['placement'], (1 if participant['placement'] <= 4 else 0), name, api_name, i + 1))

            # traits
            notable_traits = []  # for recognising the composition, into comp_encoded
            candidate_traits = []
            for trait in participant['traits']:
                if trait['tier_current'] > 0:
                    api_name = trait['name']
                    if len(notable_traits) < 3 and api_name in TRAIT_TO_ENCODED:
                        if trait['tier_current'] >= 3:
                            notable_traits.append(TRAIT_TO_ENCODED[api_name] + str(trait['tier_current']))
                        else:
                            if not (trait['tier_current'] == 1 and trait['tier_total'] == 1):
                                candidate_traits.append(TRAIT_TO_ENCODED[api_name] + str(trait['tier_current']))
                    cursor.execute("""
                        INSERT INTO trait_states (apiName, puuid, match_id, tier_current)
                        VALUES (?, ?, ?, ?)
                    """, (api_name, participant['puuid'], match_id, trait['tier_current'],))
                    cursor.execute("""SELECT sum_placement FROM traits 
                                    WHERE apiName = ? AND tier_current = ?""", (api_name, trait['tier_current']))
                    r = cursor.fetchone()
                    if not r:
                        cursor.execute("""INSERT INTO traits (apiName, tier_current, sum_placement, num_placement, top4)
                                     VALUES (?, ?, ?, 1, ?)""", (
                            api_name, trait['tier_current'], participant['placement'],
                            (1 if participant['placement'] <= 4 else 0)))
                    elif r[0] is None:
                        cursor.execute("""UPDATE traits SET sum_placement = ?, num_placement = 1, top4 = ? 
                        WHERE apiName = ? AND tier_current = ?""", (
                            participant['placement'], (1 if participant['placement'] <= 4 else 0), api_name,
                            trait['tier_current']))
                    else:
                        cursor.execute("""UPDATE traits 
                            SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                            WHERE apiName = ? AND tier_current = ?
                        """, (participant['placement'], (1 if participant['placement'] <= 4 else 0), api_name,
                              trait['tier_current']))
            if len(notable_traits) < 3:
                if candidate_traits:
                    candidate_traits.sort(key=lambda x: x[1], reverse=True)
                    candidate_traits.sort(key=lambda x: x[0])
                    notable_traits += candidate_traits[:3 - len(notable_traits)]
            notable_traits.sort(key=lambda x: x[0])
            comp_encoded = ''
            if 1 <= len(notable_traits) <= 3:
                comp_encoded = ''.join(notable_traits)
            elif not notable_traits:
                comp_encoded = 'lg'
                for augment in augments:
                    if 'Traitless' in augment:
                        comp_encoded = 'bd'
                        break
                if comp_encoded == 'lg':
                    print([unit for unit in participant['units']])
                    print(participant['placement'])
                    print('-------------------')
            else:
                print('comp_encoded error')
            if comp_encoded != '':
                # update comps
                cursor.execute("SELECT sum_placement FROM comps WHERE encoded = ?", (comp_encoded,))
                r = cursor.fetchone()
                if not r:
                    cursor.execute("""INSERT INTO comps (encoded, sum_placement, num_placement, top4) 
                        VALUES (?, ?, 1, ?)""", (
                        comp_encoded, participant['placement'], (1 if participant['placement'] <= 4 else 0)))
                elif r[0] is None:
                    cursor.execute("""UPDATE comps SET sum_placement = ?, num_placement = 1, top4 = ? 
                        WHERE encoded = ?""", (
                        participant['placement'], (1 if participant['placement'] <= 4 else 0), comp_encoded))
                else:
                    cursor.execute("""UPDATE comps 
                        SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                            WHERE encoded = ?""", (
                        participant['placement'], (1 if participant['placement'] <= 4 else 0), comp_encoded))

            cursor.execute("""
                INSERT INTO player_states (puuid, match_id, augment1, augment2, augment3, comp_encoded, placement)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                participant['puuid'], match_id, augments[0], augments[1], augments[2], comp_encoded,
                participant['placement'],))

            # units
            for unit in participant['units']:
                # update items avg
                items = unit['itemNames']
                for item in items:
                    name = ITEM_AUGMENT_MAP.get(item, '')
                    if item is not None:
                        cursor.execute('SELECT sum_placement FROM items WHERE apiName = ?', (item,))
                        r = cursor.fetchone()
                        if not r:
                            cursor.execute("""INSERT INTO items (apiName, name, sum_placement, num_placement, top4) 
                            VALUES (?, ?, ?, 1, ?)""", (
                                item, name, participant['placement'], (1 if participant['placement'] <= 4 else 0)))
                        elif r[0] is None:
                            cursor.execute('''UPDATE items 
                            SET name = ?, sum_placement = ?, num_placement = 1, top4 = ? WHERE apiName = ?''', (
                                name, participant['placement'], (1 if participant['placement'] <= 4 else 0), item))
                        else:
                            cursor.execute('''UPDATE items 
                            SET name = ?, sum_placement = sum_placement + ?, 
                            num_placement = num_placement + 1, top4 = top4 + ? WHERE apiName = ?''', (
                                name, participant['placement'], (1 if participant['placement'] <= 4 else 0), item))
                while len(items) < 3:
                    items.append(None)
                cursor.execute("""
                    INSERT INTO unit_states (apiName, puuid, match_id, tier, item1, item2, item3)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    unit['character_id'], participant['puuid'], match_id, unit['tier'], items[0], items[1], items[2]))
                # update units avg
                cursor.execute('SELECT sum_placement FROM units WHERE apiName = ?', (unit['character_id'],))
                r = cursor.fetchone()
                if not r:
                    cursor.execute('''INSERT INTO units (apiName, rarity, sum_placement, num_placement, top4) 
                    VALUES (?, ?, ?, 1, ?)''', (unit['character_id'], unit['rarity'],
                                                participant['placement'], (1 if participant['placement'] <= 4 else 0)))
                elif r[0] is None:
                    cursor.execute('''UPDATE units SET rarity = ?, sum_placement = ?, num_placement = 1, top4 = ? 
                    WHERE apiName = ?''', (unit['rarity'], participant['placement'],
                                           (1 if participant['placement'] <= 4 else 0), unit['character_id']))
                else:
                    cursor.execute("""UPDATE units 
                    SET rarity = ?, sum_placement = sum_placement + ?, 
                    num_placement = num_placement + 1, top4 = top4 + ? 
                    WHERE apiName = ?""", (unit['rarity'], participant['placement'],
                                           (1 if participant['placement'] <= 4 else 0), unit['character_id']))
                # update units_3 avg
                if unit['tier'] == 3 and (unit['rarity'] in [0, 1, 2]):  # 3-star units for tier 3 and below
                    cursor.execute('SELECT sum_placement FROM units_3 WHERE apiName = ?',
                                   (unit['character_id'],))
                    r = cursor.fetchone()
                    if not r:
                        cursor.execute(
                            '''INSERT INTO units_3 (apiName, sum_placement, num_placement, top4) VALUES (?, ?, 1, ?)'''
                            , (unit['character_id'], participant['placement'],
                               (1 if participant['placement'] <= 4 else 0)))
                    if r[0] is None:
                        cursor.execute('''UPDATE units_3 SET sum_placement = ?, num_placement = 1, top4 = ? 
                        WHERE apiName = ?''', (
                            participant['placement'], (1 if participant['placement'] <= 4 else 0),
                            unit['character_id']))
                    else:
                        cursor.execute("""UPDATE units_3 
                        SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                        WHERE apiName = ?
                        """, (participant['placement'], (1 if participant['placement'] <= 4 else 0),
                              unit['character_id']))


def summoner_to_matches(cursor, server, region, summonerName, count=10) -> list:
    if summonerName == '' or summonerName is None:
        return []
    '''return list_of_matches'''
    puuid = name_to_puuid(server, server_to_region(server), summonerName)

    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        if res.status_code == 403:
            print(summonerName)
        if res.status_code == 429:
            time.sleep(25)
            summoner_to_matches(cursor, server, region, summonerName, count)
        else:
            return []
    # print('found summoner!')

    list_of_matches = res.json()
    return list_of_matches


def server_to_matches(cursor, server, region):
    '''
        from a given server, insert 10 closest matches from each of 2000 players to the database.
        for now only challengers and gms (~1000ish) with current rate limit.
    '''

    challengers = get_league(cursor, server, region, 'challenger')
    grandmasters = get_league(cursor, server, region, 'grandmaster')
    # mastercnt = 2000 - len(challengers) - len(grandmasters)
    # masters = get_league(cursor, server, region, 'master', 200)
    for i, name in enumerate(challengers):
        # print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        if list_of_matches:
            for match in list_of_matches:
                if match:
                    insert_match(cursor, server, region, match)
    for i, name in enumerate(grandmasters):
        # print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        if list_of_matches:
            for match in list_of_matches:
                if match:
                    insert_match(cursor, server, region, match)
    # for i, name in enumerate(masters):
    #     print(f"player {i}")
    #     list_of_matches = summoner_to_matches(cursor, server, region, name, count=20)
    #     if list_of_matches:
    #         for match in list_of_matches:
    # if match:
    #     insert_match(cursor, server, region, match)


def get_league(cursor, server, region, league, mastercnt=0) -> list:
    """league: challenger, grandmaster, master, diamond, emerald, platinum, gold, silver, bronze, iron
       return list of summonerName for 3 high-elo tiers, empty list for the rests"""

    headers = {'X-Riot-Token': RIOT_API}

    if league in ['challenger', 'grandmaster', 'master']:
        high_url = f"https://{server}.api.riotgames.com/tft/league/v1/{league}"
        res = requests.get(high_url, headers=headers)
        if res.status_code != 200:
            print(res.status_code)
            if res.status_code == 429:
                time.sleep(25)
                get_league(cursor, server, region, league, mastercnt)
            else:
                print("check status code")
                return []
        json = res.json()
        if league == 'master':
            print(f'{league}s count in {server}: {len(json["entries"])}')
            summonerNames = [x['summonerName'] for x in json['entries'] if x['leaguePoints'] > 0]
            if len(summonerNames) <= mastercnt:
                return summonerNames
            return random.sample(summonerNames, mastercnt)
        print(f'{league}s count in {server}: {len(json["entries"])}')
        return [x['summonerName'] for x in json['entries']]
    else:
        league = league.upper()
        league_cnt = 0
        for division in ['I', 'II', 'III', 'IV']:
            page = 1
            while page:
                low_url = f"https://{server}.api.riotgames.com/tft/league/v1/entries/{league}/{division}?queue=RANKED_TFT&page={page}"
                res = requests.get(low_url, headers=headers)
                if res.status_code != 200:
                    print(res.status_code)
                    if res.status_code == 429:
                        time.sleep(30)
                        res = requests.get(low_url, headers=headers)
                    else:
                        print("a new status code")
                        return []
                league_cnt += len(res.json())
                if len(res.json()) == 0:
                    break
                page += 1
        print(f'{league.lower()}s count in {server}: {league_cnt}')
        return []


def string_to_canon(cursor, user_input: str):
    prefix, word = user_input.strip().split(' ', 1)
    if prefix == 'u':
        cursor.execute("SELECT apiName FROM units WHERE name LIKE ?", (f'%{word}%',))
    elif prefix == 't':
        cursor.execute("SELECT apiName FROM traits WHERE name LIKE ?", (f'%{word}%',))
    elif prefix == 'ic':
        cursor.execute("SELECT apiName FROM items WHERE class = 'craftable' and name LIKE ?", (f'%{word}%',))
    elif prefix == 'ir':
        cursor.execute("SELECT apiName FROM items WHERE class = 'radiant' and name LIKE ?", (f'%{word}%',))
    elif prefix == 'ia':
        cursor.execute("SELECT apiName FROM items WHERE class = 'ornn' and name LIKE ?", (f'%{word}%',))
    elif prefix == 'is':
        cursor.execute("SELECT apiName FROM items WHERE class = 'support' and name LIKE ?", (f'%{word}%',))
    elif prefix == 'a':
        cursor.execute("SELECT apiName FROM augments WHERE name LIKE ?", (f'%{word}%',))
    r = cursor.fetchone()
    if not r:
        raise ValueError(f"cannot find {word}")
    return r[0]


def name_to_puuid(server, region, summonerName):
    if not summonerName:
        return ''
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        if res.status_code == 429:
            time.sleep(25)
            name_to_puuid(server, region, summonerName)
        return
    json = res.json()
    return json['puuid']


def check_db(cursor, file, server: str, version):
    file.write(f"Server: {server.upper()} - {version}\n")
    cursor.execute("SELECT COUNT(*) FROM matches")
    file.write(f"matches: {cursor.fetchone()[0]}\n")
    cursor.execute("SELECT COUNT(*) FROM player_states")
    file.write(f"player_states: {cursor.fetchone()[0]}\n")
    cursor.execute("SELECT COUNT(*) FROM unit_states")
    file.write(f"unit_states: {cursor.fetchone()[0]}\n")
    cursor.execute("SELECT COUNT(*) FROM trait_states")
    file.write(f"trait_states: {cursor.fetchone()[0]}\n\n")


if __name__ == "__main__":
    main()
