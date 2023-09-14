# tasks that require manual intervention
import sqlite3
import requests

con = sqlite3.connect("raw_matches.db")
con.isolation_level = None
cur = con.cursor()

cur.execute('SELECT name, tier_current FROM traits')
rows = cur.fetchall()
for row in rows:
    name, tier_current = row[0], row[1]
    cur.execute('''
        SELECT SUM(ps.placement) 
                FROM player_states ps INNER JOIN trait_states ts 
                ON ps.puuid = ts.puuid AND ps.match_id = ts.match_id
                WHERE ts.name = ? AND ts.tier_current = ?;
    ''', (name, tier_current))
    sum_placement = cur.fetchone()[0]
    cur.execute('''
        SELECT COUNT(ps.placement) 
                FROM player_states ps INNER JOIN trait_states ts 
                ON ps.puuid = ts.puuid AND ps.match_id = ts.match_id
                WHERE ts.name = ? AND ts.tier_current = ?;
    ''', (name, tier_current))
    num_placement = cur.fetchone()[0]
    cur.execute('UPDATE traits SET sum_placement = ?, num_placement = ? WHERE name = ? and tier_current = ?',
                (sum_placement, num_placement, name, tier_current))
cur.execute('SELECT name, tier_current, CAST(sum_placement AS REAL) / num_placement AS avg FROM traits')
rows = cur.fetchall()
print(rows)
li = []
for row in rows:
    name, tier_current, avg = row[0], row[1], row[2]
    if avg is not None:
        li.append((name, tier_current, avg))
li.sort(key=lambda x: x[2])
for name, tier_current, avg in li:
    print(f"average placement of tier {tier_current} {name} is {avg:.2f}")

con.close()
