# -*- coding: utf-8 -*-

from .core import *

__author__ = 'lundberg'


# Init as singleton for easy use in Django
# You can use it like this:
# import graphdb as db
# get_node(db.manager, 'node_id')
graphdb = GraphDB.get_instance()

neo4jdb = graphdb.manager  # Works as the old neo4jdb
