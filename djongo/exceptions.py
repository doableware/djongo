djongo_access_url = 'https://www.patreon.com/nesdis'
_printed_features = set()


class SQLDecodeError(ValueError):

    def __init__(self, err_sql=None):
        self.err_sql = err_sql


class NotSupportedError(ValueError):

    def __init__(self, keyword=None):
        self.keyword = keyword


class MigrationError(Exception):

    def __init__(self, field):
        self.field = field


def print_warn(feature=None, message=None):
    if feature not in _printed_features:
        message = ((message or f'This version of djongo does not support "{feature}" fully. ')
                   + f'Visit {djongo_access_url}')
        print(message)
        _printed_features.add(feature)