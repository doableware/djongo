---
title: Database Configuration
permalink: "/database-configuration/"
---

The following options are supported in `settings.py`:

```python
    DATABASES = {
        'default': {
            'ENGINE': 'djongo',
            'NAME': 'your-db-name',
            'HOST': 'host-name or ip address',
            'PORT': port_number,
            'USER': 'db-username',
            'PASSWORD': 'password',
            'AUTH_SOURCE': 'db-name',
            'AUTH_MECHANISM': 'SCRAM-SHA-1',
        }
    }
```