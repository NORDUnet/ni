# -*- coding: utf-8 -*-

import os
import unittest
import time
import atexit
from socket import error as SocketError

from .core import init_db
import collections
collections.Callable = collections.abc.Callable

__author__ = 'lundberg'


class Neo4jTemporaryInstance(object):
    """
    Singleton to manage a temporary Neo4j instance

    Use this for testing purpose only. The instance is automatically destroyed
    at the end of the program.

    """
    _instance = None
    _http_port = None
    _bolt_port = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            atexit.register(cls._instance.shutdown)
        return cls._instance

    def __init__(self):
        self._host = 'neo4j'
        self._http_port = 7474
        self._bolt_port = 7687

        for i in range(300):
            time.sleep(0.5)
            try:
                auth = os.environ.get('NEO4J_AUTH', 'neo4j/testing').split('/')
                self._db = init_db('bolt://{!s}:{!s}'.format(self.host, self.bolt_port), username=auth[0] or 'neo4j',
                                   password=auth[1] or 'testing', encrypted=False)
            except SocketError:
                continue
            else:
                break
        else:
            self.shutdown()
            assert False, 'Cannot connect to the neo4j test instance'

    @property
    def db(self):
        return self._db

    @property
    def host(self):
        return self._host

    @property
    def http_port(self):
        return self._http_port

    @property
    def bolt_port(self):
        return self._bolt_port

    def purge_db(self):
        q = """
            MATCH (n:Node)
            OPTIONAL MATCH (n)-[r]-()
            DELETE n,r
            """
        with self.db.session as s:
            s.run(q)

    def shutdown(self):
        pass


class Neo4jTestCase(unittest.TestCase):
    """
    Base test case that sets up a temporary Neo4j instance
    """

    neo4j_instance = Neo4jTemporaryInstance.get_instance()
    neo4jdb = neo4j_instance.db

    def tearDown(self):
        self.neo4j_instance.purge_db()
