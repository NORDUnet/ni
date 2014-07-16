# -*- coding: utf-8 -*-
"""
Created on 2012-10-18 2:01 PM

@author: lundberg
"""

from django.test.simple import DjangoTestSuiteRunner
from shutil import rmtree
import norduniclient as nc
import sys


class NiwebTestSuiteRunner(DjangoTestSuiteRunner):
    """
    A test runner that sets up a temporary neo4j embedded database
    in /tmp/testneo4jdb/ and removes it on test completion.
    """

    neo4j_uri = '/tmp/testneo4jdb'

    def setup_databases(self, **kwargs):
        # Close db started by norduni client
        nc._close_db()
        nc.neo4jdb = nc.open_db(self.neo4j_uri)
        return super(NiwebTestSuiteRunner, self).setup_databases(**kwargs)

    def teardown_test_environment(self, **kwargs):
        return super(NiwebTestSuiteRunner, self).teardown_test_environment(**kwargs)

    def teardown_databases(self, old_config, **kwargs):
        nc._close_db()
        rmtree(self.neo4j_uri)
        return super(NiwebTestSuiteRunner, self).teardown_databases(old_config, **kwargs)