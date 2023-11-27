# tasks that require manual intervention
import sqlite3
import requests
import re
from itertools import permutations

IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
EXCEPTIONS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
con = sqlite3.connect("raw_matches.db")
con.isolation_level = None
cur = con.cursor()

def pool(cursor, file, i_augments=[], i_units=[], i_traits=[]):
    '''
        i_augments: a list of max length 3 of augments, unordered
        i_units: a 8x3 list, with the first being character_id, second being tier, third being item in the form of lists
        i_traits: a 8x2 list, with the first being name, the second being tier. Remember to make it so names are unique later
    '''
    inputs = [[i_augments,'p','player_states',None,None,'augment'],
              [i_units,'u','unit_states','character_id','tier','item'],
              [i_traits,'t','trait_states','name','tier_current',None]
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
                    innerjoin = f"INNER JOIN {table} {alias}{i+1} ON {alias}1.puuid = {alias}{i+1}.puuid AND {alias}1.match_id = {alias}{i+1}.match_id "
                    subquery += innerjoin
                if alias != 'p':
                    wheres.append(f"{alias}{i+1}.{primary} = '{cur[0][i]}'")
                if alias != 'p' and cur[1][i] != 0:
                    wheres.append(f"{alias}{i+1}.{secondary} = {cur[1][i]}")
                if (alias == 'u' and cur[2][i] != []) or (alias == 'p' and cur != []):
                    trio = cur
                    inner_query = ""
                    if alias == 'u':
                        trio = cur[2][i]
                    if len(trio) == 1:
                        inner_query = f"{alias}{i+1}.{tertiary}1 = '{trio[0]}' OR {alias}{i+1}.{tertiary}2 = '{trio[0]}' OR {alias}{i+1}.{tertiary}3 = '{trio[0]}'"
                    else:
                        all_items = []
                        if len(trio) == 2:
                            all_permutations = [(1,2),(2,1),(1,3),(3,1),(2,3),(3,2)]
                            for x, y in all_permutations:
                                statement = f"({alias}{i+1}.{tertiary}{x} = '{trio[0]}' AND {alias}{i+1}.{tertiary}{y} = '{trio[1]}')"
                                all_items.append(statement)
                        elif len(trio) == 3:
                            all_permutations = list(permutations(trio))
                            for perm in all_permutations:
                                statement = f"({alias}{i+1}.{tertiary}1 = '{perm[0]}' AND {alias}{i+1}.{tertiary}2 = '{perm[1]}' AND {alias}{i+1}.{tertiary}3 = '{perm[2]}')"
                                all_items.append(statement)
                        inner_query = " OR ".join(all_items)
                    wheres.append(f"({inner_query})")
            subquery = subquery + where_statement + " AND ".join(wheres)
            # print(subquery)
            subqueries.append([subquery, alias])
    if len(subqueries) == 1:
        cursor.execute(subqueries[0][0])
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

pool(cur, '', i_augments=[], i_units=[['bard','mf'],[3,0],[['shojin','gs'],['guinsoo','db','ie']]], i_traits=[['jazz','rapidfire'],[1,3]])
# pool(i_augments=['jazz baby'], i_units=[], i_traits=[])
# pool(i_augments=[], i_units=[['bard','mf'],[3,0],[['shojin','gs'],['guinsoo','db','ie']]], i_traits=[])
# pool(i_augments=[], i_units=[], i_traits=[['jazz','rapidfire'],[1,3]])



con.close()
