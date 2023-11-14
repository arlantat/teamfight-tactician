# tasks that require manual intervention
import sqlite3
import requests
import re

IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
EXCEPTIONS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
con = sqlite3.connect("raw_matches.db")
# con.isolation_level = None
cur = con.cursor()

def update_best_items(file, cursor):
    cursor.execute('''SELECT us.item1, us.item2, us.item3, ps.placement, us.tier, us.character_id 
                FROM unit_states us INNER JOIN player_states ps
                ON us.match_id = ps.match_id AND us.puuid = ps.puuid
        ''')
    rs = cursor.fetchall()
    unit_map = {} # dictionary of unit: item_map
    for r in rs:
        items = r[:3]
        placement = r[3]
        tier = r[4]
        unit = r[5]
        if unit not in unit_map:
            unit_map[unit] = {} # dictionary of item: [sum, cnt]
        for item in items:
            if item is not None:
                if item not in unit_map[unit]:
                    unit_map[unit][item] = [placement, 1]
                else:
                    unit_map[unit][item][0] += placement
                    unit_map[unit][item][1] += 1
    best_units = {}  # item: [cnt, avrg, unit]
    for unit, item_map in unit_map.items():
        li = []
        for item, val in item_map.items():
            avrg = val[0]/val[1]
            li.append((val[1], avrg, item))
            if item in EXCEPTIONITEMS or item in IGNOREDITEMS:
                continue
            if item not in best_units:
                best_units[item] = []
            best_units[item].append([val[1], avrg, unit])
        # first sort by matches
        li.sort(key=lambda s: s[0], reverse=True)

        ornn1 = [s for s in li if (re.search(r'.*Shimmerscale.+$', s[2]) and s[2] not in EXCEPTIONITEMS)]
        ornn2 = [s for s in li if (re.search(r'.*Ornn.+$', s[2]) and s[2] not in EXCEPTIONITEMS)]
        ornn = sorted((ornn1 + ornn2), key=lambda s: s[0], reverse=True)
        radiant = [s for s in li if (s[2].endswith('Radiant') and s[2] not in EXCEPTIONITEMS)]
        emblem = [s for s in li if (s[2].endswith('Emblem') and s[2] not in EXCEPTIONITEMS)]
        all_nonnormals = [s[2] for s in (ornn+radiant+emblem)] + IGNOREDITEMS
        normal = [s for s in li if s[2] not in all_nonnormals]

        # now sort by avrg
        best_normals = sorted(normal[:7], key=lambda x: x[1])
        best_radiants = sorted(radiant[:5], key=lambda x: x[1])
        best_emblems = sorted(emblem[:3], key=lambda x: x[1])
        best_ornns = sorted(ornn[:3], key=lambda x: x[1])
        file.write('---------BEST ITEMS---------\n')
        file.write(f"best normals for {unit} are {[(s[2], round(s[1], 2)) for s in best_normals]}\n")
        file.write(f"best radiants for {unit} are {[(s[2], round(s[1], 2)) for s in best_radiants]}\n")
        file.write(f"best emblems for {unit} are {[(s[2], round(s[1], 2)) for s in best_emblems]}\n")
        file.write(f"best ornns for {unit} are {[(s[2], round(s[1], 2)) for s in best_ornns]}\n")
    
    # best units for each item, same process
    file.write('---------BEST UNITS---------\n')
    for item in best_units:
        best_units[item].sort(key=lambda s: s[0], reverse=True)
        # if item in normal: unimplemented
        li = sorted(best_units[item][:7], key=lambda x: x[1])
        file.write(f"best units for {item} are {[(s[2], round(s[1], 2)) for s in li]}\n")

cur.execute('''
    SELECT us.item1, us.item2, us.item3
            FROM unit_states us INNER JOIN trait_states ts 
            ON us.puuid = ts.puuid AND us.match_id = ts.match_id
            WHERE ts.name = 'Set9_Demacia' AND ts.tier_current = 4 AND us.character_id = 'TFT9_Fiora';
''')
rows = cur.fetchall()
for on, tw, th in rows[:10]:
    print(on, tw, th)

# cur.execute('SELECT character_id FROM units')
# character_ids =  cur.fetchall()
# for row in character_ids:
#     character_id = row[0]
#     cur.execute('''SELECT us.item1, us.item2, us.item3, ps.placement
#                 FROM player_states ps INNER JOIN unit_states us
#                 ON ps.puuid = us.puuid AND ps.match_id = us.match_id
#                 WHERE us.character_id = ?
#                 ''', (character_id,))
#     rows = cur.fetchall()
#     for r in rows:
#         item1, item2, item3, placement = row[0], row[1], row[2], row[3]

# for item in li:
#     cur.execute('''
#         INSERT INTO items (name, class) VALUES (?, ?)
#     ''', (item, ))
    # cur.execute('''
    #     SELECT SUM(ps.placement) 
    #             FROM player_states ps INNER JOIN trait_states ts 
    #             ON ps.puuid = ts.puuid AND ps.match_id = ts.match_id
    #             WHERE ts.name = ? AND ts.tier_current = ?;
    # ''', (name, tier_current))
    # sum_placement = cur.fetchone()[0]
    # cur.execute('''
    #     SELECT COUNT(ps.placement) 
    #             FROM player_states ps INNER JOIN trait_states ts 
    #             ON ps.puuid = ts.puuid AND ps.match_id = ts.match_id
    #             WHERE ts.name = ? AND ts.tier_current = ?;
    # ''', (name, tier_current))
    # num_placement = cur.fetchone()[0]
    # cur.execute('UPDATE traits SET sum_placement = ?, num_placement = ? WHERE name = ? and tier_current = ?',
    #             (sum_placement, num_placement, name, tier_current))
# cur.execute('SELECT name, CAST(sum_placement AS REAL) / num_placement AS avg FROM augments')
# rows = cur.fetchall()
# li = []
# for row in rows:
#     name, avg = row[0], row[1]
#     if avg is not None:
#         li.append((name, avg))
# li.sort(key=lambda x: x[1])
# for name, avg in li:
#     print(f"average placement of {name} is {avg:.2f}")

con.close()
