# tasks that require manual intervention
import sqlite3
import requests

con = sqlite3.connect("raw_matches.db")
# con.isolation_level = None
cur = con.cursor()
cur.execute("ALTER TABLE traits ADD COLUMN sum_placement INTEGER")
cur.execute("ALTER TABLE traits ADD COLUMN num_placement INTEGER")
cur.execute('SELECT name FROM traits')
rows = cur.fetchall()
for row in rows:
    name = row[0]
    cur.execute('''
        SELECT SUM(ps.placement) 
                FROM player_states ps INNER JOIN trait_states ts 
                ON ps.puuid = ts.puuid AND ps.match_id = ts.match_id
                WHERE ts.name = ?;
    ''', (name,))
    sum_placement = cur.fetchone()[0]
    cur.execute('''
        SELECT COUNT(ps.placement) 
                FROM player_states ps INNER JOIN trait_states ts 
                ON ps.puuid = ts.puuid AND ps.match_id = ts.match_id
                WHERE ts.name = ?;
    ''', (name,))
    num_placement = cur.fetchone()[0]
    cur.execute('UPDATE traits SET sum_placement = ?, num_placement = ? WHERE name = ?',
                (sum_placement, num_placement, name))
cur.execute('SELECT name, CAST(sum_placement AS REAL) / num_placement AS avg FROM traits')
rows = cur.fetchall()
li = []
for row in rows:
    name, avg = row[0], row[1]
    li.append((name, avg))
li.sort(key=lambda x: x[1])
for name, avg in li:
    print(f"average placement of {name} is {avg:.2f}")

con.close()
