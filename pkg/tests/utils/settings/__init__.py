import sys

DEBUG = False

ALLOWED_HOSTS = ['localhost','127.0.0.1']

LOGGING = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(name)-15s:: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'default',
        },
        'null': {
            'class': 'logging.NullHandler'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console',],
    },
    'loggers': {
        'paramiko': {
            'handlers': ['null'],
            'propagate': False
        },
        'djongo': {
            'level': 'INFO'
        },
    },
}

DATABASES = {
    'djongo': {
        'ENGINE': 'djongo',
        'NAME': 'djongo-test',
        'ENFORCE_SCHEMA': True,
        'CLIENT': {
            'host': '127.0.0.1',
            'port': 27017,
        },
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'djongo-test',
    }
}

SECRET_KEY = "django_tests_secret_key"

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
