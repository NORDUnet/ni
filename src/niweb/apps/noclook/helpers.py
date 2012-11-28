# -*- coding: utf-8 -*-
"""
Created on Mon Apr  2 11:17:57 2012

@author: lundberg
"""

from django.template.defaultfilters import slugify
import socket
from django.conf import settings as django_settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db import IntegrityError, transaction
from datetime import datetime, timedelta
import csv, codecs, cStringIO
import xlwt


try:
    from niweb.apps.noclook.models import NodeHandle, NordunetUniqueId, UniqueIdGenerator, NodeType
except ImportError:
    from apps.noclook.models import NodeHandle, NordunetUniqueId, UniqueIdGenerator, NodeType
from norduni_client_exceptions import UniqueNodeError
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

def get_nh_node(node_handle_id):
    """
    Takes a node handle id and returns the node handle and the node.
    """
    nh = get_object_or_404(NodeHandle, pk=node_handle_id)
    node = nh.get_node()
    return nh, node

def form_update_node(user, node, form, property_keys=None):
    """
    Take a node, a form and the property keys that should be used to fill the
    node if the property keys are omitted the form.base_fields will be used.
    Returns True if all non-empty properties where added else False and
    rollbacks the node changes.
    """
    if not property_keys:
        property_keys = []
    meta_fields = ['relationship_location', 'relationship_end_a',
                   'relationship_end_b', 'relationship_parent',
                   'relationship_provider', 'relationship_end_user',
                   'relationship_customer', 'relationship_depends_on']
    nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
    if not property_keys:
        for field in form.base_fields.keys():
            if field not in meta_fields:
                property_keys.append(field)
    for key in property_keys:
        try:
            if form.cleaned_data[key] or form.cleaned_data[key] == 0:
                pre_value = node.getProperty(key, '')
                if pre_value != form.cleaned_data[key]:
                    with nc.neo4jdb.transaction:
                        node[key] = form.cleaned_data[key]
                    if key == 'name':
                        nh.node_name = form.cleaned_data[key]
                    nh.modifier = user
                    nh.save()
                    update_node_search_index(nc.neo4jdb, node)
            elif not form.cleaned_data[key] and key != 'name':
                with nc.neo4jdb.transaction:
                    del node[key]
                if key in django_settings.SEARCH_INDEX_KEYS:
                    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
                    nc.del_index_item(nc.neo4jdb, index, key)
        except KeyError:
            return False
        except Exception:
            # If the property type differs from what is allowed in node
            # properties. Force string as last alternative.
            with nc.neo4jdb.transaction:
                node[key] = unicode(form.cleaned_data[key])
    return True

def form_to_generic_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    node_type = slug_to_node_type(slug, create=True)
    node_handle = NodeHandle(node_name=node_name,
        node_type=node_type,
        node_meta_type=node_meta_type,
        modifier=request.user, creator=request.user)
    node_handle.save()
    set_noclook_auto_manage(nc.neo4jdb, node_handle.get_node(), False)
    return node_handle

def form_to_unique_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    node_type = slug_to_node_type(slug, create=True)
    try:
        node_handle = NodeHandle.objects.get(node_name=node_name, node_type=node_type)
        raise UniqueNodeError(node_handle.get_node())
    except NodeHandle.DoesNotExist:
        node_handle = NodeHandle.objects.create(node_name=node_name,
            node_type=node_type,
            node_meta_type=node_meta_type,
            modifier=request.user,
            creator=request.user)
        set_noclook_auto_manage(nc.neo4jdb, node_handle.get_node(), False)
    return node_handle

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

def slug_to_node_type(slug, create=False):
    """
    Returns or creates and returns the NodeType object from the supplied slug.
    """
    acronym_types = ['odf'] # TODO: Move to sql db
    if create:
        node_type, created = NodeType.objects.get_or_create(slug=slug)
        if created:
            if slug in acronym_types:
                type_name = slug.upper()
            else:
                type_name = slug.replace('-', ' ').title()
            node_type.type = type_name
            node_type.save()
    else:
        node_type = get_object_or_404(NodeType, slug=slug)
    return node_type

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
        MATCH node-[:Has*1..]->porta<-[r0?:Connected_to]-cable-[r1:Connected_to]->portb<-[?:Has*1..]-end
        RETURN node,porta,r0,cable,r1,portb,end
        '''
    return nc.neo4jdb.query(q, id=equipment.getId())

def get_depends_on_equipment(equipment):
    """
    Get all the nodes Has or Depends_on relationships.
    """
    q = '''
        START node=node({id})
        MATCH node-[?:Has*1..]->port<-[:Depends_on|Part_of]-port_logical, node<-[?:Depends_on]-direct_logical
        RETURN port, port_logical, direct_logical
        '''
    return nc.neo4jdb.query(q, id=equipment.getId())

# Alternative get_depends_on_equipment query
#q = '''
#START node=node({id})
#MATCH node-[?:Has*1..]->port<-[:Depends_on]-port_logical
#WITH node, port, collect(port_logical) as port_logicals
#MATCH node<-[?:Depends_on]-direct_logical
#return port, port_logicals, collect(direct_logical) as direct_logicals
#'''

def get_depends_on_router(router):
    """
    Get all router ports and what depends on them.
    :param router: Neo4j node
    :return: Cypher query iterator
    """
    q = '''
        START router=node({id})
        MATCH router-[:Has]->port<-[?:Depends_on|Part_of]-logical
        RETURN port, collect(logical) as depends_on_port
        ORDER BY port.name
        '''
    return nc.neo4jdb.query(q, id=router.getId())

def get_depends_on_unit(unit):
    """
    Get all logical nodes that depends on the Unit.
    :param unit: Neo4j node
    :return: Cypher query iterator
    """
    q = '''
        START unit=node({id})
        MATCH unit<-[:Depends_on]-logical
        RETURN logical as depends_on_unit
        ORDER BY logical.name
        '''
    return nc.neo4jdb.query(q, id=unit.getId())

def get_logical_depends_on(logical):
    """
    Get all nodes that the logical node depends on and their top parent if any.
    """
    q = '''
        START node=node({id})
        MATCH node-[dep_rel:Depends_on|Part_of]->dep
        WITH dep,dep_rel
        MATCH dep<-[?:Has*1..]-parent, dep-[?:Part_of]->parent<-[?:Has*1..]-grand_parent
        RETURN dep,dep_rel,parent,grand_parent
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

def get_customer(service):
    """
    Get all nodes with Uses relationship and node_type Customer.
    """
    q = '''
        START node=node({id})
        MATCH node<-[rel:Uses]-customer
        WHERE customer.node_type = "Customer"
        RETURN customer, rel
        '''
    return nc.neo4jdb.query(q, id=service.getId())

def get_end_user(service):
    """
    Get all nodes with Uses relationship and node_type End User.
    """
    q = '''
        START node=node({id})
        MATCH node<-[rel:Uses]-end_user
        WHERE end_user.node_type = "End User"
        RETURN end_user, rel
        '''
    return nc.neo4jdb.query(q, id=service.getId())

def get_services_dependent_on_cable(cable):
    """
    Get top services that depends on the supplied cable.
    :param cable: Neo4j node
    :return: Cypher ExecutionResult
    """
    q = '''
        START node=node({id})
        MATCH node-[:Connected_to]->equip
        WITH equip
        MATCH equip<-[:Depends_on*1..]-service<-[r?:Depends_on]-()
        WHERE (service.node_type = 'Service') AND (r is null)
        WITH distinct service
        MATCH service<-[:Uses]-user
        WHERE user.node_type = 'Customer'
        RETURN service, collect(user) as customers
        '''
    return nc.neo4jdb.query(q, id=cable.getId())

def get_services_dependent_on_equipment(equipment):
    """
    Get top services that depends on the supplied cable.
    :param equipment: Neo4j node
    :return: Cypher ExecutionResult
    """
    q = """
        START node=node({id})
        MATCH node-[:Has|Depends_on]-()<-[:Depends_on*1..]-service<-[r?:Depends_on]-()
        WHERE (service.node_type = 'Service') AND (r is null)
        WITH distinct service
        MATCH service<-[:Uses]-user
        WHERE user.node_type = 'Customer'
        RETURN service, collect(user) as customers
        """
    return nc.neo4jdb.query(q, id=equipment.getId())

def get_port(parent_name, port_name):
    """
    Parents should be uniquely named and ports should be uniquely named for each parent.
    :param parent_name: String
    :param port_name: String
    :return:port Neo4j node
    """
    q = '''
        START parent=node:search(name = {parent})
        MATCH parent-[Has*1..]->port
        WHERE port.node_type = "Port" and port.name = {port}
        RETURN port
        '''
    hits = nc.neo4jdb.query(q, parent=parent_name, port=port_name)
    try:
        port = [hit['port'] for hit in hits][0]
    except IndexError:
        port = None
    return port

def create_port(parent_name, parent_type, port_name, creator):
    """
    Creates a port with the supplied parent.
    :param parent_name: String
    :param port_name: String
    :param parent_type: String
    :param creator: Django user
    :return: Neo4j node
    """
    type_port = NodeType.objects.get(type="Port")
    type_parent = NodeType.objects.get(type=parent_type)
    nh = NodeHandle.objects.create(
        node_name = port_name,
        node_type = type_port,
        node_meta_type = 'Physical',
        modifier=creator, creator=creator
    )
    parent_nh = NodeHandle.objects.get(node_name=parent_name, node_type=type_parent)
    place_child_in_parent(nh.get_node(), parent_nh.node_id)
    return nh.get_node()


def place_physical_in_location(nh, node, location_id):
    """
    Places a physical node in a rack or on a site. Also converts it to a
    physical node if it still is a logical one.
    """
    # Check if the node is logical
    meta_type = nc.get_node_meta_type(node)
    if meta_type == 'logical':
        with nc.neo4jdb.transaction:
            # Make the node physical
            nc.delete_relationship(nc.neo4jdb,
                iter2list(node.Contains.incoming)[0])
            physical = nc.get_meta_node(nc.neo4jdb, 'physical')
            nc._create_relationship(nc.neo4jdb, physical, node, 'Contains')
            nh.node_meta_type = 'physical'
            nh.save()
            # Convert Uses relationships to Owns.
            user_relationships = node.Uses.incoming
            for rel in user_relationships:
                set_owner(node, rel.start.id)
                nc.delete_relationship(nc.neo4jdb, rel)
    location_node = nc.get_node_by_id(nc.neo4jdb,  location_id)
    rel_exist = nc.get_relationships(node, location_node, 'Located_in')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        # Remove the old location(s) and create a new
        for rel in iter2list(node.Located_in.outgoing):
            nc.delete_relationship(nc.neo4jdb, rel)
        nc.create_relationship(nc.neo4jdb, node,
            location_node, 'Located_in')
    return nh, node

def place_child_in_parent(node, parent_id):
    """
    Places a child node in a parent node with a Has relationship.
    """
    parent_node = nc.get_node_by_id(nc.neo4jdb,  parent_id)
    rel_exist = nc.get_relationships(parent_node, node, 'Has')
    # If the parent is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        # Remove the old parent(s) and create a new
        for rel in iter2list(node.Has.incoming):
            nc.delete_relationship(nc.neo4jdb, rel)
        nc.create_relationship(nc.neo4jdb, parent_node,
            node, 'Has')
    return node

def connect_physical(node, other_node_id):
    """
    Connects a cable to a physical node.
    """
    other_node = nc.get_node_by_id(nc.neo4jdb,  other_node_id)
    rel_exist = nc.get_relationships(node, other_node, 'Connected_to')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        nc.create_relationship(nc.neo4jdb, node, other_node,
            'Connected_to')
    return node

def set_owner(node, owner_node_id):
    """
    Creates or updates an Owns relationship between the node and the
    owner node.
    Returns the node.
    """
    owner_node = nc.get_node_by_id(nc.neo4jdb,  owner_node_id)
    rel_exist = nc.get_relationships(node, owner_node, 'Owns')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        nc.create_relationship(nc.neo4jdb, owner_node, node,
            'Owns')
    return node

def set_user(node, user_node_id):
    """
    Creates or updates an Uses relationship between the node and the
    owner node.
    Returns the node.
    """
    user_node = nc.get_node_by_id(nc.neo4jdb,  user_node_id)
    rel_exist = nc.get_relationships(node, user_node, 'Uses')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        nc.create_relationship(nc.neo4jdb, user_node, node,
            'Uses')
    return node

def set_provider(node, provider_node_id):
    """
    Creates or updates an Provides relationship between the node and the
    owner node.
    Returns the node.
    """
    provider_node = nc.get_node_by_id(nc.neo4jdb,  provider_node_id)
    rel_exist = nc.get_relationships(node, provider_node, 'Provides')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        # Remove the old provider and create a new
        for rel in iter2list(node.Provides.incoming):
            nc.delete_relationship(nc.neo4jdb, rel)
        nc.create_relationship(nc.neo4jdb, provider_node, node,
            'Provides')
    return node

def set_depends_on(node, depends_on_node_id):
    """
    Creates or updates an Depends_on relationship between the node and the
    owner node.
    Returns the node.
    """
    depends_on_node_id = nc.get_node_by_id(nc.neo4jdb,  depends_on_node_id)
    rel_exist = nc.get_relationships(node, depends_on_node_id, 'Depends_on')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        nc.create_relationship(nc.neo4jdb, node, depends_on_node_id,
            'Depends_on')
    return node

def get_hostname_from_address(ip_address):
    """
    Return the DNS name for an IP address or an empty string if
    any error occurred.
    """
    socket.setdefaulttimeout(0.5)
    try:
        return socket.gethostbyaddr(str(ip_address))[0]
    except (socket.herror, socket.gaierror):
        return 'Request timed out'

def get_collection_unique_id(unique_id_generator, unique_id_collection):
    """
    Return the next available unique id by counting up the id generator until an available id is found
    in the unique id collection.
    :param unique_id_generator: UniqueIdGenerator instance
    :param unique_id_collection: UniqueId subclass instance
    :return: String unique id
    """
    created = False
    while not created:
        id = unique_id_generator.get_id()
        obj, created = unique_id_collection.objects.get_or_create(unique_id=id)
    return id

def register_unique_id(unique_id_collection, unique_id):
    """
    Creates a new Unique ID or unreserves an already created but reserved id.
    :param unique_id_collection: Instance of a UniqueId subclass.
    :param unique_id: String
    :return: True for success, False for failure.
    """
    obj, created = unique_id_collection.objects.get_or_create(unique_id=unique_id)
    if not created and not obj.reserved:
        raise IntegrityError('ID: %s already in the db and in use.' % unique_id)
    elif obj.reserved: # ID was reserved, unreserv it.
        obj.reserved = False
        obj.save()
    return True

# TODO: Maybe move this to settings.py?
def unique_id_map(slug):
    """
    :param slug: A slug that specifies the type of object that we want to generate ID for.
    :return: Tuple of UniqueIdGenerator instance and an optional subclass of UniqueId collection.
    """
    m = {
        'nordunet-cable': (UniqueIdGenerator.objects.get(name='nordunet_cable_id'), NordunetUniqueId),
    }
    return m[slug]

def bulk_reserve_id_range(start, end, unique_id_generator, unique_id_collection, reserve_message, reserver):
    """
    Reserves IDs start to end in the format used in the unique id generator in the unique id collection without
    incrementing the unique ID generator.

    bulk_reserve_ids(100, 102, nordunet_service_unique_id_generator, nordunet_unique_id_collection...) would try to
    reserve NU-S000100, NU-S000101 and NU-S000102 in the NORDUnet unique ID collection.

    :param start: Integer
    :param end: Integer
    :param unique_id_generator: Instance of UniqueIdGenerator
    :param unique_id_collection: Instance of UniqueId subclass
    :param reserve_message: String
    :param reserver: Django user object
    :return: List of reserved unique_id_collection objects.
    """
    reserve_list = []
    prefix = suffix = ''
    if unique_id_generator.prefix:
        prefix = unique_id_generator.prefix
    if unique_id_generator.suffix:
        suffix = unique_id_generator.suffix
    for id in range(start, end+1):
        reserve_list.append(unique_id_collection(
            unique_id= '%s%s%s' % (prefix, str(id).zfill(unique_id_generator.base_id_length), suffix),
            reserved = True,
            reserve_message = reserve_message,
            reserver = reserver,
        ))
    unique_id_collection.objects.bulk_create(reserve_list)
    return reserve_list

def reserve_id_sequence(num_of_ids, unique_id_generator, unique_id_collection, reserve_message, reserver):
    """
    Reserves IDs by incrementing the unique ID generator.
    :param num_of_ids: Number of IDs to reserve.
    :param unique_id_generator: Instance of UniqueIdGenerator
    :param unique_id_collection: Instance of UniqueId subclass
    :param reserve_message: String
    :param reserver: Django user object
    :return: List of dicts with reserved ids, reserve message and eventual error message.
    """
    reserve_list = []
    for x in range(0, num_of_ids):
        id = unique_id_generator.get_id()
        error_message = ''
        try:
            sid = transaction.savepoint()
            unique_id_collection.objects.create(unique_id=id, reserved=True,
                reserve_message=reserve_message, reserver=reserver)
            transaction.savepoint_commit(sid)
        except IntegrityError:
            transaction.savepoint_rollback(sid)
            error_message = 'ID already in database. Manual check needed.'
        reserve_list.append({'id': id, 'reserve_message': reserve_message, 'error_message': error_message})
    return reserve_list