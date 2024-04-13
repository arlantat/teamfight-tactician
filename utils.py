import json
import os
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def init_request_session():
    """Initialize a session with retries for requests."""
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session


def fetch_json(url):
    response = requests.get(url)
    response.raise_for_status()  # Raise exception if invalid response
    return response.json()


def update_json_data_from_web(pbe=False):
    client = 'latest'
    if pbe:
        client = 'pbe'
    tft_vn = f'https://raw.communitydragon.org/{client}/cdragon/tft/vi_vn.json'
    tft_en = f'https://raw.communitydragon.org/{client}/cdragon/tft/en_us.json'
    data = fetch_json(tft_vn)
    with open('tft_vn.json', 'w') as f:
        json.dump(data, f, indent=4)
    data = fetch_json(tft_en)
    with open('tft_en.json', 'w') as f:
        json.dump(data, f, indent=4)


def update_item_augment_map():
    update_json_data_from_web()
    with open('tft_en.json') as f:
        tft_data = json.load(f)
        item_augment_data = tft_data['items']
    name_map = {}
    for item_augment in item_augment_data:
        if item_augment['name']:
            name_map[item_augment['apiName']] = item_augment['name']
    with open('item_augment_map.json', 'w') as f:
        json.dump(name_map, f, indent=4)


def init_encoded_traits():
    """Encode traits by highest breakpoints to be used for comps.
        trait_to_encoded transforms apiName into letter, encoded_to_trait transforms letter into name."""
    encoded_map = []
    with open('tft_en.json') as f:
        tft_data = json.load(f)
        current_set_data = tft_data['sets'][CURRENT_SET]
        traits = current_set_data['traits']
        for trait in traits:
            breakpoints = len(trait['effects'])
            highest_breakpoint = trait['effects'][-1]['minUnits']
            if breakpoints > 1:
                encoded_map.append((trait['apiName'], breakpoints, highest_breakpoint, trait['name']))
    encoded_map.sort(key=lambda x: x[1])
    encoded_map.sort(key=lambda x: x[2], reverse=True)
    trait_to_encoded = {}
    encoded_to_trait = {}
    for i, trait in enumerate(encoded_map):
        trait_to_encoded[trait[0]] = chr(i + 65)
        encoded_to_trait[chr(i + 65)] = trait[3]
    return trait_to_encoded, encoded_to_trait


def get_current_version():
    url = 'https://ddragon.leagueoflegends.com/api/versions.json'
    data = fetch_json(url)
    # return data[0]
    # return only until the second dot
    return f"Version {data[0][:data[0].rfind('.')]}"


def get_trait_name(cursor, name, tier):
    cursor.execute('SELECT name FROM traits WHERE name LIKE ? AND tier_current = ?', (f'%{name}%', tier))
    return cursor.fetchone()[0]


def item_in_class(cursor, name, class_name):
    cursor.execute('SELECT * FROM items WHERE name = ? AND class = ?', (name, class_name))
    return cursor.fetchone()


def server_to_region(server):
    return MAPPINGS[server]


load_dotenv()

RIOT_API = os.environ.get('RIOT_API')
MY_PUUID = os.environ.get('MY_PUUID')
MY_SERVER = os.environ.get('MY_SERVER')
MY_REGION = os.environ.get('MY_REGION')
CURRENT_VERSION = get_current_version()
CURRENT_SET = '11'
SERVERS = ['br1', 'eun1', 'euw1', 'jp1', 'kr', 'la1', 'la2', 'na1', 'oc1', 'ph2', 'ru', 'sg2', 'th2', 'tr1', 'tw2',
           'vn2']
REGIONS = ['americas', 'asia', 'europe', 'sea']
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
