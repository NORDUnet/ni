# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 14:26:53 2011

@author: lundberg
"""

"""
Old tests

import shutil
import norduniclient as nc

# Database will be deleted upon successful test.
TESTDB_URI = '/tmp/neo4jtestdb'

nc.neo4jdb.shutdown()
nc.test_db_setup(TESTDB_URI)
db = nc.open_db(TESTDB_URI)

print '''
Creating nodes and relationships:
se-tug.nordu.net Router 1
ge-1/2/3 PIC 3
-------------------------------------------------------------
'''
# Create a physical node
router_node = nc.create_node(db, 'se-tug.nordu.net', 'Router')
print router_node['name'], router_node['node_type'], router_node.id

# Create a relationship between the physical meta node and the new node.
with db.transaction:
    m = nc.get_meta_node(db, 'physical')
    m.Contains(router_node)

# Create another physical node    
pic_node = nc.create_node(db, 'ge-1/2/3', 'PIC')
print pic_node['name'], pic_node['node_type'], pic_node.id

# Create a relationship between the physical meta node and the new node,
# also create a relationship between the old physical node and the new one.
with db.transaction:
    m = nc.get_meta_node(db, 'physical')
    m.Contains(pic_node)
    r = nc.get_node_by_value(db, 'se-tug.nordu.net', 'name')[0]
    r.Has(pic_node)

# Check the state of the database
print '''
Database should now look like this:
(0)
(0)--[Consists_of,0]-->(2)
(0)--[Consists_of,0]-->(2)--[Contains,1]-->(1)
(0)--[Consists_of,0]-->(2)--[Contains,1]-->(1)--[Has,3]-->(3)
-------------------------------------------------------------
'''
root = nc.get_root_node(db)
for path in db.traversal().traverse(root):
    print path

# Index tests
print '''
Indexing and retriving a PIC node:
Node Type: PIC
Node Type: PIC
-------------------------------------------------------------
'''
with db.transaction:
    pic_node['test_key'] = 'Hello World!'
node_index = nc.get_node_index(db, 'test_index') 
nc.add_index_item(db, node_index, pic_node, 'test_key')
hits = node_index['test_key']['Hello World!']
for item in hits:
    print 'Node Type: %s' % item['node_type']
hits = node_index.query('all:*')
for item in hits:
    print 'Node Type: %s' % item['node_type']
    
print '''
Indexing and retriving a Has relationship:
Relationship Type: Has
Relationship Type: Has
-------------------------------------------------------------
'''
has_rel = pic_node.Has.single
with db.transaction:
    has_rel['test_key'] = 'Hello World!'
relationship_index = nc.get_relationship_index(db, 'test_index') 
nc.add_index_item(db, relationship_index, has_rel, 'test_key')
hits = relationship_index['test_key']['Hello World!']
for item in hits:
    print 'Relationship Type: %s' % item.type
hits = relationship_index.query('all:*')
for item in hits:
    print 'Relationship Type: %s' % item.type

# Function tests
# get_all_meta_nodes()
print '''
Output should now look like this:
root
physical
-------------------------------------------------------------
'''
for meta_node in nc.get_all_meta_nodes(db):
    print meta_node['name']

print '\nAll tests done, removing the test database.'
db.shutdown()
shutil.rmtree(TESTDB_URI)
"""