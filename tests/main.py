from django.core import management

import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
management.call_command('test')