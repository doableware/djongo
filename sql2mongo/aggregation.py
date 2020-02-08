from djongo.sql2mongo import NotSupportedError
from djongo import djongo_access_url

print(f'This version of djongo does not support aggregation. Visit {djongo_access_url}')
raise NotSupportedError('aggregation')
