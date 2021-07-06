---
title: Database Transactions
layout: server
permalink: /database-transactions/
---


## Transaction and Commit 

Djongo integrates with MongoDB Transactions API to support multi document atomic transactions. [Atomic transactions](https://docs.djangoproject.com/en/3.0/topics/db/transactions/) are enabled in Django using the usual `transaction.atomic()` decorator or context manager. MongoDB transactions significantly speed up Django test execution and validation.

### Example

```python
from djongo import transaction

def viewfunc(request):
    stuff()

    with transaction.atomic():
        # This code executes inside a transaction.
        more_stuff()
```

This produces the following pymongo commands:

```python
session = cli.start_session()
transaction = session.start_transaction()
# more_stuff
transaction.commit_transaction() # or transaction.abort_transaction()
session.end_session()
```
