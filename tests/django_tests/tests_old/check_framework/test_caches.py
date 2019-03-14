from django.core.checks.caches import E001
from django.test import SimpleTestCase
from django.test.utils import override_settings


class CheckCacheSettingsAppDirsTest(SimpleTestCase):
    VALID_CACHES_CONFIGURATION = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }
    INVALID_CACHES_CONFIGURATION = {
        'other': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }

    @property
    def func(self):
        from django.core.checks.caches import check_default_cache_is_configured
        return check_default_cache_is_configured

    @override_settings(CACHES=VALID_CACHES_CONFIGURATION)
    def test_default_cache_included(self):
        """
        Don't error if 'default' is present in CACHES setting.
        """
        self.assertEqual(self.func(None), [])

    @override_settings(CACHES=INVALID_CACHES_CONFIGURATION)
    def test_default_cache_not_included(self):
        """
        Error if 'default' not present in CACHES setting.
        """
        self.assertEqual(self.func(None), [E001])
