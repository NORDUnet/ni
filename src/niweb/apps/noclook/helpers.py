# -*- coding: utf-8 -*-
"""
Created on Mon Apr  2 11:17:57 2012

@author: lundberg
"""

from django.template.defaultfilters import slugify
import socket
from django.conf import settings as django_settings
from datetime import datetime, timedelta
import csv, codecs, cStringIO
import xlwt
from django.http import HttpResponse

try:
    from niweb.apps.noclook.models import NodeHandle
except ImportError:
    from apps.noclook.models import NodeHandle
import norduni_client as nc

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def get_node_url(node):
    """
    Takes a node and returns it's NodeHandles URL or '' if node
    is None.
    """
    try:
        nh = NodeHandle.objects.get(pk=node['handle_id'])
        return nh.get_absolute_url()
    except TypeError:
        # Node is most likely a None value
        return ''

def set_noclook_auto_manage(db, item, auto_manage):
    """
    Sets the node or relationship noclook_auto_manage flag to True or False. 
    Also sets the noclook_last_seen flag to now.
    """
    with db.transaction:
        item['noclook_auto_manage'] = auto_manage
        item['noclook_last_seen'] = datetime.now().isoformat()
    return True
    
def update_noclook_auto_manage(db, item):
    """
    Updates the noclook_auto_manage and noclook_last_seen properties. If 
    noclook_auto_manage is not set, it is set to True.
    """
    with db.transaction:
        try:
            item['noclook_auto_manage']
        except KeyError:
            item['noclook_auto_manage'] = True
        item['noclook_last_seen'] = datetime.now().isoformat()
    return True

def update_node_search_index(db, node):
    """
    Adds or updates the node values in the search index.
    """
    node_keys = node.getPropertyKeys()
    index = nc.get_node_index(db, nc.search_index_name())
    for key in django_settings.SEARCH_INDEX_KEYS:
        if key in node_keys:
            nc.update_index_item(db, index, node, key)

def update_relationship_search_index(db, rel):
    """
    Adds or updates the relationship values in the search index.
    """
    rel_keys = rel.getPropertyKeys()
    index = nc.get_relationship_index(db, nc.search_index_name())
    for key in django_settings.SEARCH_INDEX_KEYS:
        if key in rel_keys:
            nc.update_index_item(db, index, rel, key)

def isots_to_dt(item):
    """
    Returns noclook_last_seen property as a datetime.datetime. If the property
    does not exist we return datetime.datetime.min (0001-01-01 00:00:00).
    """
    try:
        ts = item['noclook_last_seen'] # ex. 2011-11-01T14:37:13.713434
        dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f')
    except KeyError:
        dt = datetime.min
    return dt

def neo4j_data_age(item):
    """
    Checks the noclook_last_seen property against datetime.datetime.now() and
    if the differance is greater that django_settings.NEO4J_MAX_DATA_AGE and the
    noclook_auto_manage is true the data is said to be expired.
    Returns noclook_last_seen as a datetime and a "expired" boolean.
    """
    max_age = timedelta(hours=int(django_settings.NEO4J_MAX_DATA_AGE))
    now = datetime.now()
    last_seen = isots_to_dt(item)
    expired = False
    if (now-last_seen) > max_age and item.getProperty('noclook_auto_manage', False):
        expired = True
    return last_seen, expired

def iter2list(pythonic_iterator):
    """
    Converts a neo4j.util.PythonicIterator to a list.
    """
    return [item for item in pythonic_iterator]

def item2dict(item):
    """
    Returns the item properties as a dictionary.
    """
    d = {}
    for key, value in item.items():
        d[key] = value
    return d

def nodes_to_csv(node_list, header=None):
    """
    Takes a list of nodes and returns a comma separated file with all node keys
    and their values.
    """
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=result.csv; charset=utf-8;'
    writer = UnicodeWriter(response, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
    if not header:
        key_set = set()
        for node in node_list:
            key_set.update(node.propertyKeys)
        key_set = sorted(key_set)
    else:
        key_set = header
        writer.writerow(key_set) # Line collection with header
    for node in node_list: 
        line = []
        for key in key_set:
            try:
                line.append('%s' % unicode(node[key]))
            except KeyError:
                line.append('') # Node did not have that key, add a blank item.
        writer.writerow(line)
    return response

def nodes_to_xls(node_list, header=None):
    """
    Takes a list of nodes and returns an Excel file of all node keys and their values.
    """
    # Create the HttpResponse object with the appropriate Excel header.
    response = HttpResponse(mimetype='application/excel')
    response['Content-Disposition'] = 'attachment; filename=result.xls;'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('NOCLook result')
    if not header:
        key_set = set()
        for node in node_list:
            key_set.update(node.propertyKeys)
        key_set = sorted(key_set)
    else:
        key_set = header
    # Write header
    for i in range(0, len(key_set)):
        ws.write(0, i, key_set[i])
    # Write body
    for i in range(0, len(node_list)):
        for j in range(0, len(key_set)):
            try:
                ws.write(i+1, j, unicode(node_list[i][key_set[j]]))
            except KeyError:
                ws.write(i+1, j, unicode(''))
    wb.save(response)
    return response

def nodes_to_json(node_list):
    """
    Takes a list of nodes and returns a json formatted text with all node keys
    and their values.
    """
    # TODO:
    pass

def nodes_to_geoff(node_list):
    """
    Takes a list of nodes and returns geoff format with all node keys
    and their values.
    """
    # TODO:
    pass
    
#def get_location(node):
#    """
#    Returns a list of the nodes locations as dicts with name and url.
#    """
#    location = []
#    rels = iter2list(node.Located_in.outgoing)
#    for rel in rels:
#        if rel.end['node_type'] == 'Rack':
#            # Get where the rack is placed
#            location += get_place(rel.end)
#            name = rel.end['name']
#        else:
#            name = rel.end['name']
#        location.append({'node': rel.end, 'name': name})
#    return location

#def get_place(node):
#    """
#    Returns the nodes place in site or other equipment.
#    """
#    location = []
#    rels = iter2list(node.Has.incoming)
#    for rel in rels:
#        name = rel.start['name']
#        location.append({'node': rel.start, 'name': name})
#    return location

def get_location(node):
    """
    Returns the nodes location and the locations parent, if any.
    """
    q = '''
        START node=node({id})
        MATCH node-[loc_rel:Located_in]->loc<-[?:Has*1..]-parent
        RETURN loc,loc_rel,parent
        '''
    return nc.neo4jdb.query(q, id=node.getId())

def get_place(node):
    """
    Returns the node place and the places parent, if any.
    """
    q = '''
        START node=node({id})
        MATCH node<-[loc_rel:Has]-loc<-[?:Has*1..]-parent
        RETURN loc,loc_rel,parent
        '''
    return nc.neo4jdb.query(q, id=node.getId())

def get_connected_cables(cable):
    """
    Get the things the cable is connected to and their parents, if any.
    """
    from operator import itemgetter
    connected = []
    q = '''                   
        START node=node({id})
        MATCH node-[r0:Connected_to]->port<-[?:Has*1..10]-end
        RETURN node, r0, port, end
        '''
    hits = nc.neo4jdb.query(q, id=cable.getId())
    for hit in hits:
        connected.append({'cable': hit['node'], 'rel': hit['r0'], 
                          'port': hit['port'], 'end': hit['end']})
    connected = sorted(connected, key=itemgetter('port')) 
    return connected

def get_connected_equipment(equipment):
    """
    Get all the nodes Has relationships and what they are connected to.
    """
    q = '''
        START node=node({id})
        MATCH node-[:Has*1..10]->porta<-[r0?:Connected_to]-cable-[r1:Connected_to]->portb<-[?:Has*1..10]-end
        RETURN node,porta,r0,cable,r1,portb,end
        '''
    return nc.neo4jdb.query(q, id=equipment.getId())

def get_depends_on_equipment(equipment):
    """
    Get all the nodes Has or Depends_on relationships.
    """
    q = '''
        START node=node({id})
        MATCH node-[?:Has*1..10]->port<-[?:Depends_on]-logical, node<-[?:Depends_on]-logical
        WHERE node-[:Has]->port OR node<-[:Depends_on]-logical
        RETURN node,logical,port
        '''
    return nc.neo4jdb.query(q, id=equipment.getId())

def get_logical_depends_on(logical):
    """
    Get all nodes that the logical node depends on and their top parent if any.
    """
    q = '''
        START node=node({id})
        MATCH node-[:Depends_on]->dep<-[?:Has*1..]-parent
        RETURN dep,parent
        '''
    return nc.neo4jdb.query(q, id=logical.getId())

def get_racks_and_equipment(site):
    """
    Get all the racks on a site and the equipment, if any, in those racks.
    """
    q = '''
        START node=node({id})
        MATCH node-[r0:Has]->rack<-[r1?:Located_in]-equipment
        RETURN rack,r1,equipment
        '''
    return nc.neo4jdb.query(q, id=site.getId())

def get_same_name_relations(relation):
    """
    Get all relation meta typed nodes with the same name as the provided node.
    """
    q = '''
        START node=node:search(name = {name})
        MATCH meta-[:Contains]->node
        WHERE (meta.name = 'relation') and not(node.node_type = {type})
        RETURN node as relation
        ORDER BY node.node_type
        '''
    return nc.neo4jdb.query(q, name=relation.getProperty('name', ''),
                            type=relation.getProperty('node_type', ''))

def get_units(port):
    """
    Get all Unit nodes that depend on the port.
    """
    q = '''
        START node=node({id})
        MATCH node<-[:Depends_on]-unit
        WHERE unit.node_type = "Unit"
        RETURN unit
        '''
    return nc.neo4jdb.query(q, id=port.getId())

def get_hostname_from_address(ip_address):
    """
    Return the DNS name for an IP address or an empty string if
    any error occurred.
    """
    socket.setdefaulttimeout(0.5)
    try:
        return socket.gethostbyaddr(str(ip_address))[0]
    except (socket.herror, socket.gaierror):
        return ''