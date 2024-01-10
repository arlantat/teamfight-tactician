# TF-Tactician
![Static Badge](https://img.shields.io/badge/Python-blue)
![Static Badge](https://img.shields.io/badge/SQLite-brightgreen)

The app designed to give competitive advantage to Teamfight Tactics (TFT) players by fetching match history data from the Riot API and transforming it to helpful information, including champions, traits, augments, and compositions on playrates, winrates and best combinations.

### Procedures:
Reset DB Per patch:
```python
reset_db()  # init_db.py
```

Reset DB Per set:
```python
# init_db.py
# find sample matches by invoking riot api first then
reset_db(per_set=True)
# then manually check if there are discrepancies in units and items in
manual_per_set()
# and run it.
```

### Main Functionalities:
```python
# fetch info from the top-rated ladder of the current region into SQLite
server_to_matches(db_cursor, server, region)
# update strongest compositions
update_meta(db_cursor)
# find average placement for a specified combination of augments, units, and traits
pool(db_cursor, file, i_augments=[], i_units=[], i_traits=[])
```

### Developer's Thought
As you might have noticed, I haven't yet deployed this to a web server, but I promise it is coming real soon. I have been hardstuck at Master, but after developing this app, I finally reach Challenger (which is the highest rank in the game, 2 tiers above Master for those who are unaware) only with the insight from here alone. This reinforces my love with the game and my love with programming all the same. So yeah, it's comin'.
