# tasks that require manual intervention
import sqlite3
import requests
import re
from itertools import permutations
from tft import string_to_canon, pool

IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
EXCEPTIONS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
con = sqlite3.connect("raw_matches.db")
con.isolation_level = None
cur = con.cursor()

# string_to_canon(cur, 'a supportc')
cur.execute("select num_placement from augments where name = 'TFT6_Augment_PortableForge'")
print(cur.fetchone())

    # if i_traits is not []:
    #     t_subquery = 'SELECT t1.puuid, t1.match_id FROM trait_states t1 '
    #     where = f"WHERE t1.name = '{i_traits[0]}' "
    #     for i in range(1, len(i_traits)):
    #         innerjoin = f"INNER JOIN trait_states t{i+1} ON t1.puuid = t{i+1}.puuid AND t1.match_id = t{i+1}.match_id "
    #         u_subquery += innerjoin
    #         where += f"AND t{i+1}.name = '{i_traits[i]}' "
    #     u_subquery += where
    #     query1 = '''
    #         SELECT u.puuid, u.match_id
    #             FROM (
    #                 SELECT u1.puuid, u1.match_id
    #                 FROM unit_states u1
    #                 INNER JOIN unit_states u2 ON u1.puuid = u2.puuid AND u1.match_id = u2.match_id
    #                 WHERE u1.character_id = 'a' AND u2.character_id = 'b'
    #             ) AS u
    #             JOIN (
    #                 SELECT t1.puuid, t1.match_id
    #                 FROM trait_states t1
    #                 INNER JOIN trait_states t2 ON t1.puuid = t2.puuid AND t1.match_id = t2.match_id
    #                 WHERE t1.name = 'a' AND t2.name = 'b'
    #             ) AS t ON u.puuid = t.puuid AND u.match_id = t.match_id
    #             JOIN (
    #                 SELECT p1.puuid, p1.match_id
    #                 FROM player_states p1
    #                 INNER JOIN player_states p2 ON p1.puuid = p2.puuid AND p1.match_id = p2.match_id
    #                 INNER JOIN player_states p3 ON p1.puuid = p3.puuid AND p1.match_id = p3.match_id
    #                 WHERE p1.name = 'a' AND p2.name = 'b' AND p3.name = 'c'
    #             ) AS p ON u.puuid = p.puuid AND u.match_id = p.match_id;
    #     '''

    # cur.execute(query1)
    # rs = cur.fetchall()
    # for r in rs:
    #     augment_21 = r[0]
    #     augment_32 = r[1]
    #     augment_42 = r[2]
    #     comp_encoded = r[3]
    #     placement = r[4]
    #     char = r[5]
    #     char_tier = r[6]
    #     items = r[7:10]
    #     trait = r[10]
    #     trait_tier = r[11]

# pool(cur, '', i_augments=[], i_units=[['u vex'],[0],[['ic jg','ic jg']]], i_traits=[])
# pool(i_augments=['jazz baby'], i_units=[], i_traits=[])
# pool(i_augments=[], i_units=[['bard','mf'],[3,0],[['shojin','gs'],['guinsoo','db','ie']]], i_traits=[])
# pool(i_augments=[], i_units=[], i_traits=[['jazz','rapidfire'],[1,3]])



con.close()
