# tasks that require manual intervention
import sqlite3
import requests
import re
from itertools import permutations
from tft import get_league, server_to_region


IGNOREDITEMS = ['TFT_Item_Spatula','TFT_Item_RecurveBow','TFT_Item_SparringGloves','TFT_Item_ChainVest','TFT_Item_BFSword','TFT_Item_GiantsBelt','TFT_Item_NegatronCloak','TFT_Item_NeedlesslyLargeRod','TFT_Item_TearOfTheGoddess','TFT9_HeimerUpgrade_SelfRepair','TFT9_HeimerUpgrade_MicroRockets','TFT9_HeimerUpgrade_Goldification','TFT9_Item_PiltoverCharges','TFT9_HeimerUpgrade_ShrinkRay','TFT_Item_EmptyBag','TFT9_Item_PiltoverProgress','TFT_Item_ForceOfNature']
EXCEPTIONS = ['TFT4_Item_OrnnObsidianCleaver','TFT4_Item_OrnnRanduinsSanctum','TFT7_Item_ShimmerscaleHeartOfGold','TFT5_Item_ZzRotPortalRadiant']
con = sqlite3.connect("raw_matches.db")
con.isolation_level = None
cur = con.cursor()
server = 'vn2'
region = server_to_region(server)

# string_to_canon(cur, 'a supportc')
cur.execute("select num_placement from augments where name = 'TFT6_Augment_PortableForge'")
print(cur.fetchone())

# get_league(cur, server, region, 'challenger')
# get_league(cur, server, region, 'grandmaster')
# get_league(cur, server, region, 'master')
# get_league(cur, server, region, 'diamond')
# get_league(cur, server, region, 'emerald')
get_league(cur, server, region, 'platinum')
get_league(cur, server, region, 'gold')
get_league(cur, server, region, 'silver')
get_league(cur, server, region, 'bronze')
get_league(cur, server, region, 'iron')

# pool(cur, '', i_augments=[], i_units=[['u vex'],[0],[['ic jg','ic jg']]], i_traits=[])
# pool(i_augments=['jazz baby'], i_units=[], i_traits=[])
# pool(i_augments=[], i_units=[['bard','mf'],[3,0],[['shojin','gs'],['guinsoo','db','ie']]], i_traits=[])
# pool(i_augments=[], i_units=[], i_traits=[['jazz','rapidfire'],[1,3]])



con.close()
