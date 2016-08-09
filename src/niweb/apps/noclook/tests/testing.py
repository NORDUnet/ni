# -*- coding: utf-8 -*-
from __future__ import absolute_import
import norduniclient as nc
from norduniclient.testing import Neo4jTemporaryInstance

__author__ = 'lundberg'

# Use test instance of the neo4j db
neo4j_tmp = Neo4jTemporaryInstance.get_instance()
nc.neo4jdb = neo4j_tmp.db
