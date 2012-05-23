# -*- coding: utf-8 -*-
"""
Created on Mon Apr  2 11:17:57 2012

@author: lundberg
"""

from django.template.defaultfilters import slugify
from django.conf import settings as django_settings
from datetime import datetime, timedelta

from niweb.apps.noclook.models import NodeHandle
import norduni_client as nc

def get_node_url(node):
    '''
    Takes a node and returns it's NodeHandles URL or '' if node
    is None.
    '''
    try:
        nh = NodeHandle.objects.get(pk=node['handle_id'])
        return nh.get_absolute_url()
    except TypeError:
        # Node is most likely a None value
        return ''

def set_noclook_auto_manage(db, item, auto_manage):
    '''
    Sets the node or relationship noclook_auto_manage flag to True or False. 
    Also sets the noclook_last_seen flag to now.
    '''
    with db.transaction:
        item['noclook_auto_manage'] = auto_manage
        item['noclook_last_seen'] = datetime.now().isoformat()
    return True
    
def update_noclook_auto_manage(db, item):
    '''
    Updates the noclook_auto_manage and noclook_last_seen properties. If 
    noclook_auto_manage is not set, it is set to True.
    '''
    with db.transaction:
        try:
            item['noclook_auto_manage']
        except KeyError:
            item['noclook_auto_manage'] = True
        item['noclook_last_seen'] = datetime.now().isoformat()
    return True

def isots_to_dt(item):
    '''
    Returns noclook_last_seen property as a datetime.datetime. If the property
    does not exist we return datetime.datetime.min (0001-01-01 00:00:00).
    '''
    try:
        ts = item['noclook_last_seen'] # ex. 2011-11-01T14:37:13.713434
        dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f')
    except KeyError:
        dt = datetime.min
    return dt

def neo4j_data_age(item):
    '''
    Checks the noclook_last_seen property against datetime.datetime.now() and
    if the differance is greater that django_settings.NEO4J_MAX_DATA_AGE and the
    noclook_auto_manage is true the data is said to be expired.
    Returns noclook_last_seen as a datetime and a "expired" boolean.
    '''
    max_age = timedelta(hours=int(django_settings.NEO4J_MAX_DATA_AGE))
    now = datetime.now()
    last_seen = isots_to_dt(item)
    expired = False
    if (now-last_seen) > max_age and item.getProperty('noclook_auto_manage', False):
        expired = True
    return last_seen, expired

def iter2list(pythonic_iterator):
    '''
    Converts a neo4j.util.PythonicIterator to a list.
    '''
    l = []
    for item in pythonic_iterator:
        l.append(item)
    return l

def item2dict(item):
    '''
    Returns the item properties as a dictionary.
    '''
    d = {}
    for key, value in item.items():
        d[key] = value
    return d

def nodes_to_csv(node_list):
    '''
    Takes a list of nodes and returns a comma separeted file with all node keys
    and their values.
    '''
    key_set = set()
    for node in node_list:
        key_set.update(node.propertyKeys)
    key_set = sorted(key_set)
    output = [';'.join(key_set)] # Line collection with header
    for node in node_list: 
        line = []
        for key in key_set:
            try:
                line.append('"%s"' % unicode(node[key]))
            except KeyError:
                line.append('') # Node did not have that key, add a blank item.
        output.append(';'.join(line))
    return '\n'.join(output)

def nodes_to_json(node_list):
    '''
    Takes a list of nodes and returns a json formated text with all node keys
    and their values.
    '''
    # TODO:
    pass

def nodes_to_geoff(node_list):
    '''
    Takes a list of nodes and returns geoff format with all node keys
    and their values.
    '''
    # TODO:
    pass
    
def get_location(node):
    '''
    Returns a list of the nodes locations as dicts with name and url.
    '''
    location = []
    rels = iter2list(node.Located_in.outgoing)
    for rel in rels:
        if rel.end['node_type'] == 'Rack':
            # Get where the rack is placed
            location += get_place(rel.end)
            name = rel.end['name']
        else:
            name = rel.end['name']
        location.append({'node': rel.end, 'name': name})
    return location

def get_place(node):
    '''
    Returns the nodes place in site or other equipment.
    '''
    location = []
    rels = iter2list(node.Has.incoming)
    for rel in rels:
        name = rel.start['name']
        location.append({'node': rel.start, 'name': name})
    return location
    
def get_connected_cables(cable):
    '''
    Get the things the cable is connected to and their parents, if any.
    '''
    from operator import itemgetter
    connected = []
    q = '''                   
        START node=node(%d)
        MATCH node-[r0:Connected_to]->port<-[?:Has*1..10]-end
        RETURN node, r0, port, end
        ''' % cable.id
    hits = nc.neo4jdb.query(q)
    for hit in hits:
        connected.append({'cable': hit['node'], 'rel': hit['r0'], 
                          'port': hit['port'], 'end': hit['end']})
    connected = sorted(connected, key=itemgetter('port')) 
    return connected

def get_connected_equipment(equipment):
    '''
    Get all the nodes Has relationships and what they are connected to.
    '''
    q = '''
        START node=node(%d)
        MATCH node-[:Has*1..10]->porta<-[r0?:Connected_to]-cable-[r1:Connected_to]->portb<-[?:Has*1..10]-end
        RETURN node,porta,r0,cable,r1,portb,end
        ''' % equipment.id
    return nc.neo4jdb.query(q)