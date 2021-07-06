---
title: Model Update
layout: server
permalink: /model-update/
---

## Bulk Write

MongoDB lets you perform [Bulk Write operations](https://docs.mongodb.com/manual/core/bulk-write-operations/) using [`bulk_write`](https://api.mongodb.com/python/current/api/pymongo/collection.html#pymongo.collection.Collection.bulk_write) which is currently not supported in Django. However, by using Djongo it is possible to perform bulk writes.

```python
class BulkWrite(ordered=True)
```

### Arguments

Argument | Type | Description
---------|------|-------------
`ordered` | `boolean` | Perform the write operations either in order or arbitrarily.

### Example

 ```python
from djongo import BulkWrite

with BulkWrite():
    entry = Entry.objects.get(pk=p_key) # Queries the DB once
    entry.headline = 'The Beatles reconcile'
    entry.save() # Djongo does not really do a update to MongoDB
    Entry.objects.create(name='How the beatles reconciled') # Djongo does not really do a insert to MongoDB

# On exit, does: db.entry.bulk_write([UpdateOne(), InsertOne()])
```

## Unordered Bulk Writes

### Example

 ```python
from djongo import BulkWrite

with BulkWrite(ordered=False):
    entry = Entry.objects.get(pk=p_key) # Queries the DB once
    entry.headline = 'The Beatles reconcile'
    entry.save() # Djongo does not really do a update to MongoDB
    Entry.objects.create(name='How the beatles reconciled') # Djongo does not really do a insert to MongoDB

# On exit, does: 
# db.entry.bulk_write(
#   [UpdateOne(), InsertOne()]
#   ordered=False)
```
