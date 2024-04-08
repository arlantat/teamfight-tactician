import glob
import json
import os
import sqlite3
import sys
from collections import defaultdict
from utils import CURRENT_SET, update_json_data_from_web


def init_db():
    if os.path.exists('tft_stats.db'):
        os.remove('tft_stats.db')

    con = sqlite3.connect("tft_stats.db")
    con.isolation_level = None
    cur = con.cursor()
    cur.execute("CREATE TABLE matches(match_id TEXT PRIMARY KEY)")
    cur.execute("""
        CREATE TABLE player_states (
            puuid TEXT,
            match_id TEXT,
            augment1 TEXT,
            augment2 TEXT,
            augment3 TEXT,
            comp_encoded TEXT,
            placement INTEGER,
            PRIMARY KEY (puuid, match_id)
        )
    """)
    # per set
    cur.execute("""
        CREATE TABLE units (
            apiName TEXT PRIMARY KEY,
            name TEXT,
            rarity INTEGER,
            cost INTEGER,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE units_3 (
            apiName TEXT PRIMARY KEY,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE unit_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apiName TEXT,
            puuid TEXT,
            match_id TEXT,
            tier INTEGER,
            item1 TEXT,
            item2 TEXT,
            item3 TEXT
        )
    """)
    # per set
    cur.execute("""
        CREATE TABLE traits (
            apiName TEXT,
            name TEXT,
            tier_current INTEGER,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER,
            PRIMARY KEY (apiName, tier_current)
        )
    """)
    cur.execute("""
        CREATE TABLE trait_states (
            apiName TEXT,
            puuid TEXT,
            match_id TEXT,
            tier_current INTEGER,
            PRIMARY KEY (apiName, puuid, match_id)
        )
    """)
    cur.execute("""
        CREATE TABLE items (
            apiName TEXT PRIMARY KEY,
            class TEXT,
            name TEXT,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE augments (
            apiName TEXT,
            stage INTEGER,
            name TEXT,
            class TEXT,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER,
            PRIMARY KEY (apiName, stage)
        )
    """)
    cur.execute("""
        CREATE TABLE comps (
            encoded TEXT PRIMARY KEY,
            sum_placement INTEGER,
            num_placement INTEGER,
            top4 INTEGER
        )
    """)
    con.close()


def clear_db(per_set=False):
    con = sqlite3.connect("tft_stats.db")
    con.isolation_level = None
    cur = con.cursor()
    cur.execute("DELETE FROM matches")
    cur.execute("DELETE FROM player_states")
    cur.execute("DELETE FROM unit_states")
    cur.execute("DELETE FROM trait_states")
    cur.execute("DELETE FROM augments")
    cur.execute("DELETE FROM comps")
    cur.execute("UPDATE items SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    if not per_set:
        cur.execute("UPDATE units SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
        cur.execute("UPDATE units_3 SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
        cur.execute("UPDATE traits SET sum_placement = NULL, num_placement = NULL, top4 = NULL")
    else:
        cur.execute("DELETE FROM units")
        cur.execute("DELETE FROM units_3")
        cur.execute("DELETE FROM traits")
    con.close()


def init_items_augments(cur, item_map, dir_name):
    files = glob.glob(os.path.join(dir_name, '*.txt'))
    for file in files:
        item_class = file.split('\\')[-1].split('.')[0]
        with open(file, 'r') as f:
            content = f.read()
            # read each line
            for name in content.split('\n'):
                if name:
                    try:
                        cur.execute(f"INSERT INTO {dir_name} (name, apiName, class) VALUES (?, ?, ?)",
                                    (name, item_map[name], item_class,))
                    except KeyError:
                        print(f"Augments/Items not recognized: {name}")
                        # write to file
                        with open('items_not_recognized.txt', 'a') as f:
                            f.write(f"{name}\n")


def init_per_set_v2():
    con = sqlite3.connect("tft_stats.db")
    con.isolation_level = None
    cur = con.cursor()
    with open('tft_en.json') as f:
        tft_data = json.load(f)
        current_set_data = tft_data['sets'][CURRENT_SET]
        item_augment_data = tft_data['items']
    units = current_set_data['champions']
    init_units(cur, units)
    traits = current_set_data['traits']
    init_traits(cur, traits)
    item_augment_map = {}
    name_map = {}
    if os.path.exists('items_not_recognized.txt'):
        os.remove('items_not_recognized.txt')
    for item_augment in item_augment_data:
        if item_augment['name']:
            item_augment_map[item_augment['name']] = item_augment['apiName']
            name_map[item_augment['apiName']] = item_augment['name']
    init_items_augments(cur, item_augment_map, 'items')
    # init_items_augments(cur, item_augment_map, 'augments')
    with open('item_augment_map.json', 'w') as f:
        json.dump(name_map, f, indent=4)

    con.close()


def init_units(cur, units):
    unit_dict = defaultdict(list)
    for unit in units:
        unit_dict[unit['cost']].append((unit['apiName'], unit['name']))
    for cost, units in unit_dict.items():
        for unit in units:
            cur.execute("""
                INSERT INTO units (apiName, name, cost)
                VALUES (?, ?, ?)
            """, (unit[0], unit[1], cost,))
            if cost in [1, 2, 3]:
                cur.execute("""
                    INSERT INTO units_3 (apiName)
                    VALUES (?)
                """, (unit[0],))


def init_traits(cur, traits):
    for trait in traits:
        breakpoints = len(trait['effects'])
        for i in range(1, breakpoints + 1):
            name = str(trait['effects'][i - 1]["minUnits"]) + " " + trait['name']
            cur.execute("""
                INSERT INTO traits (apiName, name, tier_current)
                VALUES (?, ?, ?)
            """, (trait['apiName'], name, i))


if __name__ == '__main__':
    update_json_data_from_web()
    # if arg 1 is 'clear', clear db
    if len(sys.argv) > 1 and sys.argv[1] == 'patch':
        clear_db()
    elif len(sys.argv) > 1 and sys.argv[1] == 'set':
        if not os.path.exists('tft_stats.db'):
            init_db()
        else:
            clear_db(per_set=True)
        init_per_set_v2()
