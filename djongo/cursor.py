from pymongo.command_cursor import CommandCursor as PymongoCommandCursor
from pymongo.cursor import Cursor as PymongoCursor
from logging import getLogger
from sql2mongo import Parse

logger = getLogger(__name__)


class Cursor:

    def __init__(self, mongo_conn):
        self.mongo_conn = mongo_conn
        self.result = None
        self.parse = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.result.close()

    def __getattr__(self, name):
        try:
            return getattr(self.result, name)
        except AttributeError:
            pass

        try:
            return getattr(self.mongo_conn, name)
        except AttributeError:
            raise

    @property
    def rowcount(self):
        if self.result is None:
            raise RuntimeError

        return self.result.count()

    @property
    def lastrowid(self):
        return self.parse.last_row_id

    def execute(self, sql, params=None):
        self.parse = Parse(self.mongo_conn, sql, params)
        self.result = self.parse.result()

    def _prefetch(self):
        if self.mongo_cursor is None:
            raise RuntimeError('Non existent cursor operation')

        if not isinstance(self.mongo_cursor, (PymongoCursor, PymongoCommandCursor)):
            return self.mongo_cursor,

        if not self.mongo_cursor.alive:
            return []

        return None

    def fetchmany(self, size=1):
        ret = []
        for _ in range(size):
            try:
                ret.append(self.result.next())
            except StopIteration:
                break

        return ret

    def fetchone(self):
        try:
            return self.result.next()
        except StopIteration:
            return []

    def fetchall(self):
        return list(self.result)

