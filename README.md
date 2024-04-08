# TF-Tactician
![Static Badge](https://img.shields.io/badge/Python-blue)
![Static Badge](https://img.shields.io/badge/SQLite-brightgreen)

Welcome to TF-Tactician - the app designed to give competitive advantage to Teamfight Tactics (TFT) players by fetching match history data from the Riot API and transforming it to helpful information, including champions, traits, augments, and compositions on playrates, winrates and best combinations.

[![TF-Tactician](https://github.com/arlantat/teamfight-tactician/assets/88363323/26f2b930-a7d7-4335-9809-54faac4f9f88)](https://youtu.be/xUiEJ9vxqnc)

### Procedures:

Once per patch:

```
$ python init.py patch
```

Once per set:
```
$ python init.py set
```

### Main Functionalities:
```python
# fetch info from the top-rated ladder of the current region into SQLite
server_to_matches
# update strongest compositions
update_meta
# find average placement for a specified combination of augments, units, and traits
pool
```
