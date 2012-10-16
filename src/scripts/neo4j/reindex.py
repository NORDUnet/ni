__author__ = 'lundberg'

# Removes the search index and reindexes all nodes and relationships.

import sys
import os

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/var/opt/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from apps.noclook import helpers as h
import norduni_client as nc

with nc.neo4jdb.transaction:
    node_index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    del node_index
    rel_index = nc.get_relationship_index(nc.neo4jdb, nc.search_index_name())
    del rel_index

print "Reindexing nodes.",
for node in nc.neo4jdb.nodes:
    h.update_node_search_index(nc.neo4jdb, node)
    print '.',
print "done."

print "Reindexing relationships.",
for rel in nc.neo4jdb.relationships:
    h.update_relationship_search_index(nc.neo4jdb, rel)
    print '.',
print "done."
