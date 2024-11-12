from settings.profiles.djongo_lite import *

INSTALLED_APPS = ['aut.apps.AutAppConfig'] + INSTALLED_APPS
DATABASES['djongo']['ENFORCE_SCHEMA'] = False