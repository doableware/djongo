from django.core import management

import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
management.call_command('test')