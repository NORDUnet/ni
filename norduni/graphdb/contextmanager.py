# -*- coding: utf-8 -*-

from contextlib import contextmanager
from .core import get_db_driver

__author__ = 'lundberg'


class Neo4jDBSessionManager:

    """
    Every new connection is a transaction. To minimize new connection overhead for many reads we try to reuse a single
    connection. If this seem like a bad idea some kind of connection pool might work better.

    Neo4jDBSessionManager.session()

    Neo4jDBSessionManager.transaction()
    """

    def __init__(self, uri, username=None, password=None, encrypted=True, max_pool_size=50):
        self.uri = uri
        self.driver = get_db_driver(uri, username, password, encrypted, max_pool_size)

    @contextmanager
    def _session(self):
        session = self.driver.session()
        try:
            yield session
        except Exception as e:
            raise e
        finally:
            try:
                session.close()
            except Exception:
                pass
    session = property(_session)

    @contextmanager
    def _transaction(self):
        session = self.driver.session()
        transaction = session.begin_transaction()
        try:
            yield transaction
        except Exception as e:
            transaction.success = False
            raise e
        else:
            transaction.success = True
        finally:
            try:
                session.close()
            except Exception:
                pass
    transaction = property(_transaction)
