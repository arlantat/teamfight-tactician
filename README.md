# convenient-bot

## TFT analyser
Have fun with TFT. Lookup players, matches, and see ranked stats.

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