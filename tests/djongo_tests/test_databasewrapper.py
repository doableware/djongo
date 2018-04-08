import unittest
from unittest.mock import patch, MagicMock

from djongo.base import DatabaseWrapper


class TestDatabaseWrapper(unittest.TestCase):
    """Test cases for connection attempts"""

    def test_empty_connection_params(self):
        """Check for returned connection params if empty settings dict is provided"""
        settings_dict = {}
        wrapper = DatabaseWrapper(settings_dict)

        params = wrapper.get_connection_params()

        self.assertEqual(params['name'], 'djongo_test')
        self.assertEqual(params['host'], 'localhost')
        self.assertEqual(params['port'], 27017)

    def test_connection_params(self):
        """Check for returned connection params if filled settings dict is provided"""
        name = MagicMock(str)
        port = MagicMock(int)
        host = MagicMock(str)

        settings_dict = {
                'NAME': name,
                'PORT': port,
                'HOST': host
        }

        wrapper = DatabaseWrapper(settings_dict)

        params = wrapper.get_connection_params()

        assert params['name'] is name
        assert params['port'] is port
        assert params['host'] is host

    @patch('djongo.base.MongoClient')
    def test_connection(self, mocked_mongoclient):
        settings_dict = MagicMock(dict)
        wrapper = DatabaseWrapper(settings_dict)

        wrapper.get_new_connection(wrapper.get_connection_params())

        mocked_mongoclient.assert_called_once()

if __name__ == '__main__':
    unittest.main()
