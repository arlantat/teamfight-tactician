import sqlite3
import logging
import requests
import os
import random
import time
import re
from dotenv import load_dotenv
load_dotenv()

def main():
    con = sqlite3.connect("raw_matches.db")
    # con.isolation_level = None
    cur = con.cursor()
    server = 'vn2'
    region = server_to_region(server) 
    players = ['KhanhTri1810','adversary','St3Mura','Noob Guy','HNZ MIDFEEDD','xayah nilah','KND Finn','H E N I S S','RoT T2','PRX f0rs4keN','TVQ 1','PRX someth1ng','KND iCynS','GGx Lemonss','temppploutmmlggs','DB HighRoll','LLAETUM','paranoise','JayDee 333','KND k1an', 'Đình Tuấn1', 'M1nhbeso', 'Nâng cúp 4 lần', 'Just Dante', 'Dòng Máu Họ Đỗ', 'Marry Shaco', 'GD Shaw1', 'Dizzyland', 'Yasuo Không Q', 'CFNP Mèo Hor1', 'Onlive TrungVla', 'y Tiger1','Cloudyyyyyyyy','INF Kiss Kiss', 'Setsuko','1atsA','Twinkling Whales','TSK Milfhunter','me from nowhere','severthaidinh','Won Joon Soo']
    for player in players:
        list_of_matches = summoner_to_matches(cur, server, region, player, count=30)
        if not list_of_matches:
            continue
        for match in list_of_matches:
            insert_match(cur, server, region, match)
    # server_to_matches(cur, server, region)
    update_meta(cur)

    check_db(cur)
    con.close()

logging.basicConfig(level=logging.INFO)
SERVERS = ['br1','eun1','euw1','jp1','kr','la1','la2','na1','oc1','ph2','ru','sg2','th2','tr1','tw2','vn2']
REGIONS = ['americas', 'asia', 'europe', 'sea']
VERSION = 'Version 13.23'

CRAFTABLES = {'TFT_Item_GargoyleStoneplate', 'TFT_Item_SpearOfShojin', 'TFT_Item_Deathblade', 'TFT_Item_AdaptiveHelm', 'TFT_Item_Redemption', 'TFT_Item_SteraksGage', 'TFT_Item_DragonsClaw', 'TFT_Item_StatikkShiv', 'TFT_Item_WarmogsArmor', 'TFT_Item_Bloodthirster', 'TFT_Item_PowerGauntlet', 'TFT_Item_BrambleVest', 'TFT_Item_GuardianAngel', 'TFT_Item_IonicSpark', 'TFT_Item_MadredsBloodrazor', 'TFT_Item_InfinityEdge', 'TFT_Item_GuinsoosRageblade', 'TFT_Item_FrozenHeart', 'TFT_Item_BlueBuff', 'TFT_Item_ThiefsGloves', 'TFT_Item_SpectralGauntlet', 'TFT_Item_RabadonsDeathcap', 'TFT_Item_LastWhisper', 'TFT_Item_RunaansHurricane', 'TFT_Item_RapidFireCannon', 'TFT_Item_HextechGunblade', 'TFT_Item_UnstableConcoction', 'TFT_Item_Crownguard', 'TFT_Item_Quicksilver', 'TFT_Item_TitansResolve', 'TFT_Item_NightHarvester', 'TFT_Item_ArchangelsStaff', 'TFT_Item_RedBuff', 'TFT_Item_JeweledGauntlet', 'TFT_Item_Leviathan', 'TFT_Item_Morellonomicon'}
RADIANTS = {'TFT5_Item_StatikkShivRadiant','TFT5_Item_LeviathanRadiant','TFT5_Item_SpectralGauntletRadiant','TFT5_Item_RunaansHurricaneRadiant','TFT5_Item_QuicksilverRadiant','TFT5_Item_MorellonomiconRadiant','TFT5_Item_BrambleVestRadiant', 'TFT5_Item_AdaptiveHelmRadiant', 'TFT5_Item_InfinityEdgeRadiant', 'TFT5_Item_HandOfJusticeRadiant', 'TFT5_Item_GuinsoosRagebladeRadiant', 'TFT5_Item_RabadonsDeathcapRadiant', 'TFT5_Item_JeweledGauntletRadiant', 'TFT5_Item_GiantSlayerRadiant', 'TFT5_Item_IonicSparkRadiant', 'TFT5_Item_SpearOfShojinRadiant', 'TFT5_Item_HextechGunbladeRadiant', 'TFT5_Item_SteraksGageRadiant', 'TFT5_Item_ThiefsGlovesRadiant', 'TFT5_Item_FrozenHeartRadiant', 'TFT5_Item_ArchangelsStaffRadiant', 'TFT5_Item_CrownguardRadiant', 'TFT5_Item_GargoyleStoneplateRadiant', 'TFT5_Item_DragonsClawRadiant', 'TFT5_Item_RapidFirecannonRadiant', 'TFT5_Item_WarmogsArmorRadiant', 'TFT5_Item_BloodthirsterRadiant', 'TFT5_Item_DeathbladeRadiant', 'TFT5_Item_LastWhisperRadiant', 'TFT5_Item_TrapClawRadiant', 'TFT5_Item_SunfireCapeRadiant', 'TFT5_Item_TitansResolveRadiant', 'TFT5_Item_NightHarvesterRadiant', 'TFT5_Item_RedemptionRadiant', 'TFT5_Item_GuardianAngelRadiant', 'TFT5_Item_BlueBuffRadiant'}
EMBLEMS = {'TFT10_Item_BigShotEmblem', 'TFT10_Item_KDAEmblem', 'TFT10_Item_SuperfanEmblem', 'TFT10_Item_GuardianEmblem', 'TFT10_Item_ExecutionerEmblem', 'TFT10_Item_CountryEmblem', 'TFT10_Item_EdgelordEmblem', 'TFT10_Item_8bitEmblem', 'TFT10_Item_PBJEmblem', 'TFT10_Item_DiscoEmblem', 'TFT10_Item_BrawlerEmblem', 'TFT10_Item_PentakillEmblem', 'TFT10_Item_FighterEmblem', 'TFT10_Item_CrowdDiverEmblem', 'TFT10_Item_RapidfireEmblem', 'TFT10_Item_TrueDamageEmblem', 'TFT10_Item_DazzlerEmblem', 'TFT10_Item_EmoEmblem', 'TFT10_Item_JazzEmblem', 'TFT10_Item_HyperPopEmblem', 'TFT10_Item_PunkEmblem', 'TFT10_Item_WardenEmblem', 'TFT10_Item_SpellweaverEmblem'}
ARTIFACTS = {'TFT9_Item_OrnnHullbreaker', 'TFT7_Item_ShimmerscaleGamblersBlade', 'TFT7_Item_ShimmerscaleMogulsMail', 'TFT9_Item_OrnnPrototypeForge', 'TFT4_Item_OrnnInfinityForce', 'TFT9_Item_OrnnDeathfireGrasp', 'TFT4_Item_OrnnAnimaVisage', 'TFT9_Item_OrnnTrickstersGlass', 'TFT7_Item_ShimmerscaleGoldmancersStaff','TFT4_Item_OrnnDeathsDefiance', 'TFT7_Item_ShimmerscaleDiamondHands', 'TFT9_Item_OrnnHorizonFocus','TFT4_Item_OrnnZhonyasParadox', 'TFT4_Item_OrnnEternalWinter', 'TFT4_Item_OrnnMuramana', 'TFT4_Item_OrnnTheCollector'}
SUPPORTS = {'TFT5_Item_ZzRotPortalRadiant','TFT4_Item_OrnnRanduinsSanctum','TFT4_Item_OrnnObsidianCleaver','TFT7_Item_ShimmerscaleHeartOfGold','TFT_Item_BansheesVeil','TFT_Item_Shroud','TFT_Item_Zephyr','TFT_Item_Chalice','TFT_Item_ZekesHerald','TFT_Item_RadiantVirtue','TFT_Item_LocketOfTheIronSolari','TFT_Item_AegisOfTheLegion'}
IGNOREDITEMS = {'TFT_Item_BFSword','TFT_Item_ChainVest','TFT_Item_EmptyBag','TFT_Item_NegatronCloak','TFT_Item_SparringGloves','TFT_Item_TearOfTheGoddess','TFT_Item_NeedlesslyLargeRod','TFT_Item_GiantsBelt','TFT_Item_RecurveBow','TFT_Item_ForceOfNature','TFT_Item_Spatula'}

IGNOREDUNITS = []
# UNITS1 = ['TFT10_Nami','TFT10_Annie','TFT10_Kennen','TFT10_Evelynn','TFT10_KSante','TFT10_Olaf','TFT10_Jinx','TFT10_Yasuo','TFT10_Lillia','TFT10_Vi','TFT10_Taric','TFT10_TahmKench','TFT10_Corki',]
# UNITS2 = ['TFT10_Garen','TFT10_Gnar','TFT10_Aphelios','TFT10_Gragas','TFT10_Seraphine','TFT10_Twitch','TFT10_Kayle','TFT10_Senna','TFT10_Kaisa','TFT10_Pantheon','TFT10_Bard','TFT10_Katarina','TFT10_Jax',]
# UNITS3 = ['TFT10_Mordekaiser','TFT10_Sett','TFT10_Amumu','TFT10_Lux','TFT10_MissFortune','TFT10_Vex','TFT10_Riven','TFT10_Urgot','TFT10_Ekko','TFT10_Samira','TFT10_Lulu','TFT10_Neeko','TFT10_Yone',]
# UNITS4 = ['TFT10_Viego','TFT10_TwistedFate','TFT10_Thresh','TFT10_Ezreal','TFT10_Akali','TFT10_Zac','TFT10_Ahri','TFT10_Caitlyn','TFT10_Karthus','TFT10_Zed','TFT10_Akali_TrueDamage','TFT10_Poppy','TFT10_Blitzcrank',]
# UNITS5 = ['TFT10_Lucian','TFT10_Yorick','TFT10_Illaoi','TFT10_Sona','TFT10_Kayn','TFT10_Jhin','TFT10_Ziggs','TFT10_Qiyana',]
# TRAITS = ['Set10_Sentinel','Set10_8Bit','Set10_Hyperpop','Set10_Spellweaver','Set10_Classical','Set10_Superfan','Set10_KDA','Set10_Edgelord','Set10_Emo','Set10_Breakout','Set10_Funk','Set10_Jazz','Set10_EDM','Set10_Dazzler','Set10_Deadeye','Set10_TwoSides','Set10_DJ','Set10_IllBeats','Set10_TrueDamage','Set10_PopBand','Set10_CrowdDive','Set10_Fighter','Set10_Country','Set10_Quickshot','Set10_PunkRock','Set10_Guardian','Set10_Pentakill','Set10_Brawler','Set10_Executioner',]
# RARITY = {0: '1 cost', 1: '2 cost', 2: '3 cost', 4: '4 cost', 6: '5 cost'}

TRAITPRIO = {  # encode for database. Traits not listed are unique traits, which won't be used by comp_encoded
    'Set10_Spellweaver': 'a', 'Set10_Pentakill': 'b',
    'Set10_KDA': 'c', 'Set10_PopBand': 'd',
    'Set10_Edgelord': 'e', 'Set10_Country': 'f',
    'Set10_TrueDamage': 'g', 'Set10_Sentinel': 'h', 'Set10_8Bit': 'i',
    'Set10_Emo': 'j', 'Set10_PunkRock': 'k',
    'Set10_Deadeye': 'l', 'Set10_Brawler': 'm',
    'Set10_CrowdDive': 'n', 'Set10_Dazzler': 'o',
    'Set10_Executioner': 'p', 'Set10_Fighter': 'q',
    'Set10_Guardian': 'r', 'Set10_Quickshot': 's',
    'Set10_Funk': 't', 'Set10_Superfan': 'u',
    'Set10_Jazz': 'v', 'Set10_EDM': 'w', 'Set10_Hyperpop': 'x'
}
TRAITREVERSE = {  # reverse mapping back to trait
    'a': 'Set10_Spellweaver', 'b': 'Set10_Pentakill',
    'c': 'Set10_KDA', 'd': 'Set10_PopBand',
    'e': 'Set10_Edgelord', 'f': 'Set10_Country',
    'g': 'Set10_TrueDamage', 'h': 'Set10_Sentinel', 'i': 'Set10_8Bit',
    'j': 'Set10_Emo', 'k': 'Set10_PunkRock',
    'l': 'Set10_Deadeye', 'm': 'Set10_Brawler',
    'n': 'Set10_CrowdDive', 'o': 'Set10_Dazzler',
    'p': 'Set10_Executioner', 'q': 'Set10_Fighter',
    'r': 'Set10_Guardian', 's': 'Set10_Quickshot',
    't': 'Set10_Funk', 'u': 'Set10_Superfan',
    'v': 'Set10_Jazz', 'w': 'Set10_EDM', 'x': 'Set10_Hyperpop'
}
MAPPINGS = {  # na1, vn2, kr confirmed
    SERVERS[0]: REGIONS[0],
    SERVERS[1]: REGIONS[2],
    SERVERS[2]: REGIONS[2],
    SERVERS[3]: REGIONS[1],
    SERVERS[4]: REGIONS[1],
    SERVERS[5]: REGIONS[0],
    SERVERS[6]: REGIONS[0],
    SERVERS[7]: REGIONS[0],
    SERVERS[8]: REGIONS[3],
    SERVERS[9]: REGIONS[1],
    SERVERS[10]: REGIONS[2],
    SERVERS[11]: REGIONS[1],
    SERVERS[12]: REGIONS[1],
    SERVERS[13]: REGIONS[2],
    SERVERS[14]: REGIONS[1],
    SERVERS[15]: REGIONS[3]
    }
RIOT_API = os.environ.get('RIOT_API')


def update_meta(cursor):
    with open('meta.txt', 'w') as file:
        update_best_items(file, cursor)
        avg(file, cursor, 'traits')
        avg(file, cursor, 'units')
        avg(file, cursor, 'units', 'maxed')
        avg(file, cursor, 'items')
        avg(file, cursor, 'augments')
        avg(file, cursor, 'comps')


# added find best units for each item here, but still want to separate it in a different module
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
    file.write('---------BEST ITEMS FOR EACH UNIT---------\n')
    for unit, item_map in unit_map.items():
        li = []
        for item, val in item_map.items():
            avrg = val[0]/val[1]
            li.append((val[1], avrg, item))
            if item in IGNOREDITEMS:
                continue
            if item not in best_units:
                best_units[item] = []
            best_units[item].append([val[1], avrg, unit])
        # first sort by matches
        li.sort(key=lambda s: s[0], reverse=True)

        # doesn't make sense to include support items here
        artifact = [s for s in li if s[2] in ARTIFACTS]
        craftable = [s for s in li if s[2] in CRAFTABLES]
        emblem = [s for s in li if s[2] in EMBLEMS]
        radiant = [s for s in li if s[2] in RADIANTS]

        # now sort by avrg
        best_craftables = sorted(craftable[:15], key=lambda x: x[1])
        best_radiants = sorted(radiant[:3], key=lambda x: x[1])
        best_emblems = sorted(emblem[:3], key=lambda x: x[1])
        best_artifacts = sorted(artifact[:3], key=lambda x: x[1])
        file.write(f"best craftables for {unit} are {[(s[2], round(s[1], 2)) for s in best_craftables]}\n")
        file.write(f"best radiants for {unit} are {[(s[2], round(s[1], 2)) for s in best_radiants]}\n")
        file.write(f"best emblems for {unit} are {[(s[2], round(s[1], 2)) for s in best_emblems]}\n")
        file.write(f"best artifacts for {unit} are {[(s[2], round(s[1], 2)) for s in best_artifacts]}\n\n")
    
    # best units for each item, same process
    file.write('---------BEST UNITS FOR EACH ITEM---------\n')
    for item in best_units:
        best_units[item].sort(key=lambda s: s[0], reverse=True)
        # if item in normal: unimplemented
        li = sorted(best_units[item][:7], key=lambda x: x[1])
        file.write(f"best units for {item} are {[(s[2], round(s[1], 2)) for s in li]}\n")


def avg(file, cursor, table, arg=None):
    '''table = traits, units, items, augments, comps.
    if 'units' is passed, arg can be 'maxed'.
    if 'items' is passed, arg can be 'normal', 'radiant', 'ornn', 'emblem'.
    if 'augments' is passed, arg can be '1', '2', '3'.
    '''
    head = 'SELECT CAST(sum_placement AS REAL) / num_placement AS avg, CAST(top4 AS REAL) / num_placement AS top4_rate'
    if table == 'traits':
        cursor.execute(f"{head}, name, tier_current FROM {table}")
    elif table == "comps":
        cursor.execute(f"{head}, encoded FROM {table} ORDER BY num_placement DESC LIMIT 30")
    elif table == 'items':
        if arg is None:
            avg(file, cursor, table, arg='craftable')
            avg(file, cursor, table, arg='radiant')
            avg(file, cursor, table, arg='artifact')
            avg(file, cursor, table, arg='emblem')
            avg(file, cursor, table, arg='support')
            return
        else:
            cursor.execute(f"{head}, name FROM {table} WHERE class = ?", (arg,))
    elif table == 'augments':
        if arg is None:
            avg(file, cursor, table, arg='1')
            avg(file, cursor, table, arg='2')
            avg(file, cursor, table, arg='3')
            return
        else:
            cursor.execute(f"{head}, name FROM {table} WHERE stage = ?", (arg,))
    elif table == 'units':
        if arg == 'maxed':
            table = 'units_3'
        cursor.execute(f"{head}, character_id FROM {table}")
    rows = cursor.fetchall()
    li = []
    for row in rows:
        avrg, top4_rate, col1, col2 = row[0], row[1], row[2], None
        if len(row) == 4:
            col2 = row[3]
        if avrg is not None:
            li.append((avrg, top4_rate, col1, col2))
    li.sort(key=lambda x: x[0])
    if arg in ['craftable', 'radiant', 'artifact', 'emblem', 'support']:
        file.write(f"---------{arg.upper()} ITEMS----------\n")
    elif arg in ['1', '2', '3']:
        file.write(f"---------AUGMENT {arg.upper()}----------\n")
    elif arg == 'maxed':
        file.write(f"---------3 STAR UNITS----------\n")
    else:
        file.write(f"--------------{table.upper()}---------------\n")
    for row in li:
        if table == 'traits':
            file.write(f"average placement of tier {row[3]} {row[2]} is {row[0]:.2f}, top 4 rate {row[1]*100:.2f}\n")
        elif table == 'comps':
            file.write(f"average placement of tier {row[2][1]} {TRAITREVERSE[row[2][0]]}, tier {row[2][3]} {TRAITREVERSE[row[2][2]]}, tier {row[2][5]} {TRAITREVERSE[row[2][4]]} is {row[0]:.2f}, top 4 rate {(row[1]*100):.2f}\n")
        else:
            # emblems from augments are removed in set 10
            # if table == 'augments' and row[2].endswith(('Trait', 'Trait2', 'Emblem', 'Emblem2')):
            #     file.write(f"average placement of {row[2]} is {row[0]:.2f}, top 4 rate {(row[1]*100):.2f} EMBLEM OR TRAIT\n")
            #     continue
            file.write(f"average placement of {row[2]} is {row[0]:.2f}, top 4 rate {(row[1]*100):.2f}\n")

def insert_match(cursor, server, region, match_id):
    # save unnecessary get requests
    cursor.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,))
    if cursor.fetchone() is not None:
        return
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        # wait and retry if rate limit exceeded
        if res.status_code == 429:
            time.sleep(25)
            insert_match(cursor, server, region, match_id)
        return
    json = res.json()
    info = json['info']
    if info['game_version'].startswith(VERSION) and info['queue_id'] == 1100:
        cursor.execute("INSERT INTO matches (match_id) VALUES (?)", (match_id,))
        for participant in info['participants']:
            # augments
            augments = participant['augments']
            for i, name in enumerate(augments):
                cursor.execute('SELECT sum_placement FROM augments WHERE name = ? AND stage = ?', (name, i+1))
                r = cursor.fetchone()
                if not r:
                    cursor.execute('''INSERT INTO augments (name, stage, sum_placement, num_placement, top4) VALUES (?, ?, ?, ?, ?)
                                ''', (name, i+1, participant['placement'], 1, (1 if participant['placement']<=4 else 0)))
                elif r[0] is None:
                    cursor.execute('''UPDATE augments SET sum_placement = ?, num_placement = 1, top4 = ? WHERE name = ? AND stage = ?'''
                                    , (participant['placement'], (1 if participant['placement']<=4 else 0), name, i+1))
                else:
                    cursor.execute('''UPDATE augments SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                                WHERE name = ? AND stage = ?''', (participant['placement'], (1 if participant['placement']<=4 else 0), name, i+1))
            while len(augments) < 3:
                augments.append(None)
            
            # traits #debug
            notable_traits = [] # for recognising the composition, into comp_encoded
            candidate_traits = []
            for trait in participant['traits']:
                if trait['tier_current'] > 0:
                    if len(notable_traits) < 3 and trait['name'] in TRAITPRIO:
                        if trait['tier_current'] >= 3:
                            notable_traits.append(TRAITPRIO[trait['name']] + str(trait['tier_current']))
                        else:
                            candidate_traits.append(TRAITPRIO[trait['name']] + str(trait['tier_current']))
                    cursor.execute("""
                        INSERT INTO trait_states (name, puuid, match_id, tier_current)
                        VALUES (?, ?, ?, ?)
                    """, (trait['name'], participant['puuid'], match_id, trait['tier_current'],))
                    cursor.execute("SELECT name, tier_current, sum_placement FROM traits WHERE name = ? AND tier_current = ?", (trait['name'],trait['tier_current']))
                    r = cursor.fetchone()
                    if not r:
                        cursor.execute("INSERT INTO traits (name, tier_current, sum_placement, num_placement, top4) VALUES (?, ?, ?, 1, ?)"
                                    , (trait['name'],trait['tier_current'],participant['placement'],(1 if participant['placement']<=4 else 0)))
                    elif r[2] is None:
                        cursor.execute("UPDATE traits SET sum_placement = ?, num_placement = 1, top4 = ? WHERE name = ? AND tier_current = ?"
                                    , (participant['placement'], (1 if participant['placement']<=4 else 0), trait['name'], trait['tier_current']))
                    else:
                        cursor.execute("""
                            UPDATE traits SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                            WHERE name = ? AND tier_current = ?
                        """, (participant['placement'], (1 if participant['placement']<=4 else 0), trait['name'], trait['tier_current']))
            if len(notable_traits) < 3:
                candidate_traits.sort(key=lambda x: x[1], reverse=True)
                candidate_traits.sort(key=lambda x: x[0])
            i = 0
            while len(notable_traits) < 3 and i < len(candidate_traits):
                notable_traits.append(candidate_traits[i])
                i += 1
            notable_traits.sort(key=lambda x: x[0])
            comp_encoded = ''.join(notable_traits)
            if comp_encoded != '':
            # update comps
                cursor.execute("SELECT encoded, sum_placement FROM comps WHERE encoded = ?", (comp_encoded,))
                r = cursor.fetchone()
                if not r:
                    cursor.execute("INSERT INTO comps (encoded, sum_placement, num_placement, top4) VALUES (?, ?, 1, ?)"
                                , (comp_encoded,participant['placement'],(1 if participant['placement']<=4 else 0)))
                elif r[1] is None:
                    cursor.execute("UPDATE comps SET sum_placement = ?, num_placement = 1, top4 = ? WHERE encoded = ?"
                                , (participant['placement'], (1 if participant['placement']<=4 else 0), comp_encoded))
                else:
                    cursor.execute("""
                        UPDATE comps SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? 
                        WHERE encoded = ?
                    """, (participant['placement'], (1 if participant['placement']<=4 else 0), comp_encoded))

            #debug
            cursor.execute("""
                INSERT INTO player_states (puuid, match_id, augment1, augment2, augment3, comp_encoded, placement)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (participant['puuid'], match_id, augments[0], augments[1], augments[2], comp_encoded, participant['placement'],))
            
            # units
            for unit in participant['units']:
                if unit['character_id'] not in IGNOREDUNITS:
                    # update items avg
                    items = unit['itemNames']
                    for item in items:
                        if item is not None or item not in IGNOREDITEMS:
                            cursor.execute('SELECT sum_placement FROM items WHERE name = ?', (item,))
                            r = cursor.fetchone()
                            if not r:
                                cursor.execute("INSERT INTO items (name, sum_placement, num_placement, top4) VALUES (?, ?, 1, ?)"
                                    , (item, participant['placement'], (1 if participant['placement']<=4 else 0)))
                            elif r[0] is None:
                                cursor.execute('''UPDATE items SET sum_placement = ?, num_placement = 1, top4 = ? WHERE name = ?'''
                                            , (participant['placement'], (1 if participant['placement']<=4 else 0), item))
                            else:
                                cursor.execute('''UPDATE items SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? WHERE name = ?'''
                                            , (participant['placement'], (1 if participant['placement']<=4 else 0), item))
                    while len(items) < 3:
                        items.append(None)
                    cursor.execute("""
                        INSERT INTO unit_states (character_id, puuid, match_id, tier, item1, item2, item3)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (unit['character_id'], participant['puuid'], match_id, unit['tier'], items[0], items[1], items[2]))
                    # update units avg
                    cursor.execute('SELECT sum_placement FROM units WHERE character_id = ?', (unit['character_id'],))
                    r = cursor.fetchone()[0]
                    if r is None:
                        cursor.execute('''UPDATE units SET sum_placement = ?, num_placement = 1, top4 = ? WHERE character_id = ?'''
                                    , (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))
                    else:
                        cursor.execute("""
                            UPDATE units SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? WHERE character_id = ?
                        """, (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))
                    # update units_3 avg
                    if unit['tier'] == 3 and (unit['rarity'] in [0, 1, 2]):  # 3 star units for tier 3 and below
                        cursor.execute('SELECT sum_placement FROM units_3 WHERE character_id = ?', (unit['character_id'],))
                        r = cursor.fetchone()[0]
                        if r is None:
                            cursor.execute('''UPDATE units_3 SET sum_placement = ?, num_placement = 1, top4 = ? WHERE character_id = ?'''
                                        , (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))
                        else:
                            cursor.execute("""
                                UPDATE units_3 SET sum_placement = sum_placement + ?, num_placement = num_placement + 1, top4 = top4 + ? WHERE character_id = ?
                            """, (participant['placement'], (1 if participant['placement']<=4 else 0), unit['character_id']))


def summoner_to_matches(cursor, server, region, summonerName, count=10) -> list:
    '''return list_of_matches'''
    puuid = name_to_puuid(server, server_to_region(server), summonerName)
    if puuid is None:
        print('cannot find summoner name!')
        return
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return []
    print('found summoner!')
    
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
    # masters = get_league(cursor, server, region, 'master', mastercnt)
    for i, name in enumerate(challengers):
        print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        if list_of_matches:
            for match in list_of_matches:
                insert_match(cursor, server, region, match)
    for i, name in enumerate(grandmasters):
        print(f"player {i}")
        list_of_matches = summoner_to_matches(cursor, server, region, name)
        if list_of_matches:
            for match in list_of_matches:
                insert_match(cursor, server, region, match)
    # for i, name in enumerate(masters):
        # print(f"player {i}")
        # list_of_matches = summoner_to_matches(cursor, server, region, name)
        # if list_of_matches:
        #     for match in list_of_matches:
        #         insert_match(cursor, server, region, match)

def get_league(cursor, server, region, league, mastercnt=0) -> list:
    '''league: master, grandmaster, master'''
    '''return list of summonerName'''

    url = f"https://{server}.api.riotgames.com/tft/league/v1/{league}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return []
    json = res.json()

    if league == 'master':
        summonerNames = [x['summonerName'] for x in json['entries'] if x['leaguePoints'] > 0]
        print(f'{league}s count in {server}: {len(json["entries"])}')
        if len(summonerNames) <= mastercnt:
            return summonerNames
        return random.sample(summonerNames, mastercnt)
    print(f'{league}s count in {server}: {len(json["entries"])}')
    return [x['summonerName'] for x in json['entries']]

def server_to_region(server):
    return MAPPINGS[server]

def name_to_puuid(server, region, summonerName):
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}"
    headers = {'X-Riot-Token': RIOT_API}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(res.status_code)
        return
    json = res.json()
    return json['puuid']

def check_db(cursor):
    cursor.execute("SELECT COUNT(*) FROM matches")
    print(f"matches: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM player_states")
    print(f"player_states: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM unit_states")
    print(f"unit_states: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM trait_states")
    print(f"trait_states: {cursor.fetchone()[0]}")

if __name__ == "__main__":
    main()
