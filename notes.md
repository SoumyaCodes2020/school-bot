# SQLite Features _(Community Moderation)_

## How to get column names

```python
cnames = []
    c.execute("""PRAGMA table_info(features);""")
    for i in c.fetchall():
        cnames.append(i[1])
```

## How to **_add_** a column to a table

```python
c.execute("""ALTER TABLE features ADD <name> <type>;""")
    db.commit()
```

## How to **_remove_** a column from a table

```python
c.execute("""ALTER TABLE features DROP <name> """)
    db.commit()
```
