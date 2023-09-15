# tasks that require manual intervention
import sqlite3
import requests

con = sqlite3.connect("raw_matches.db")
# con.isolation_level = None
cur = con.cursor()

# cur.execute('''
#     CREATE TABLE augments (
#         name TEXT PRIMARY KEY,
#         sum_placement INTEGER,
#         num_placement INTEGER
#     )
# ''')
cur.execute("SELECT augment1, augment2, augment3, placement FROM player_states")
rows = cur.fetchall()
for row in rows:
    augment1, augment2, augment3, placement = row[0], row[1], row[2], row[3]
    li = [augment1, augment2, augment3]
    for name in li:
        if name is None:
            continue
        cur.execute('SELECT name FROM augments WHERE name = ?', (name,))
        if cur.fetchone() is None:
            cur.execute('''INSERT INTO augments (name, sum_placement, num_placement)
                        VALUES (?, ?, ?)
                        ''', (name, placement, 1))
        else:
            cur.execute('''UPDATE augments SET sum_placement = sum_placement + ?, num_placement = num_placement + 1
                        WHERE name = ?
                        ''', (placement, name))
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
cur.execute('SELECT name, CAST(sum_placement AS REAL) / num_placement AS avg FROM augments')
rows = cur.fetchall()
li = []
for row in rows:
    name, avg = row[0], row[1]
    if avg is not None:
        li.append((name, avg))
li.sort(key=lambda x: x[1])
for name, avg in li:
    print(f"average placement of {name} is {avg:.2f}")

con.close()
