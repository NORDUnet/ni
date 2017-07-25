# -*- coding: utf-8 -*-
from __future__ import absolute_import
import norduniclient as nc
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

__author__ = 'lundberg'

try:
    NEO4J_URI = settings.TEST_NEO4J_URI
    NEO4J_USERNAME = settings.TEST_NEO4J_USERNAME
    NEO4J_PASSWORD = settings.TEST_NEO4J_PASSWORD
    # Use provided test database
    test_db = nc.init_db(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    nc.graphdb._manager = test_db
except ImproperlyConfigured:
    from norduniclient.testing import Neo4jTemporaryInstance
    # Use test instance of the neo4j db
    neo4j_tmp = Neo4jTemporaryInstance.get_instance()
    nc.graphdb.manager = neo4j_tmp.db
