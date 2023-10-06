# tasks that require manual intervention
import sqlite3
import requests
import re

IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
EXCEPTIONS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
con = sqlite3.connect("raw_matches.db")
# con.isolation_level = None
cur = con.cursor()

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
