import subprocess
import shutil

from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        source_database_name = self.connection.settings_dict['NAME']
        target_database_name = self.get_test_db_clone_settings(suffix)['NAME']
        try:
            host = self.connection.settings_dict['CLIENT']['host']
        except KeyError:
            host = None
        client = self.connection.client_connection
        if not keepdb:
            self._destroy_test_db(target_database_name, verbosity)
            args = [
                'mongodump',
                '--quiet',
            ]
            if host is not None:
                args += [
                    '--host',
                    host
                ]
            args += [
                '--db',
                source_database_name
            ]
            subprocess.run(args)
            args = [
                'mongorestore',
                f'dump/{source_database_name}',
                '--quiet'
            ]
            if host is not None:
                args += [
                    '--host',
                    host
                ]
            args += [
                '--db',
                target_database_name
            ]
            subprocess.run(args)
            shutil.rmtree('dump')

        print('Closing cloned connection')
        client.close()
