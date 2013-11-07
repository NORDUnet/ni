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
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from datetime import datetime, timedelta
from actstream.models import action_object_stream, target_stream
import csv
import codecs
import cStringIO
import xlwt

try:
    from niweb.apps.noclook.models import NodeHandle, NordunetUniqueId, UniqueIdGenerator, NodeType
    from niweb.apps.noclook import activitylog
except ImportError:
    from apps.noclook.models import NodeHandle, NordunetUniqueId, UniqueIdGenerator, NodeType
    from apps.noclook import activitylog
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


def normalize_whitespace(s):
    """
    Removes leading and ending whitespace from a string.
    """
    return u' '.join(s.split())

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

def delete_node(user, node):
    try:
        nh = NodeHandle.objects.get(pk=node['handle_id'])
        if nc.get_node_meta_type(node) == 'physical':
            # Remove dependant equipment like Ports and Units
            for rel in node.Has.outgoing:
                delete_node(user, rel.end)
            for rel in node.Part_of.incoming:
                delete_node(user, rel.start)
        activitylog.delete_node(user, nh)
        nh.delete()
    except (ObjectDoesNotExist, nc.neo4jdb.NotFoundException):
        pass
    return True


def delete_relationship(user, relationship):
    activitylog.delete_relationship(user, relationship)
    nc.delete_relationship(nc.neo4jdb, relationship)
    return True


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
                   'relationship_customer', 'relationship_depends_on',
                   'relationship_user', 'relationship_owner',
                   'relationship_located_in', 'relationship_ports']
    nh = get_object_or_404(NodeHandle, pk=node['handle_id'])
    if not property_keys:
        for field in form.base_fields.keys():
            if field not in meta_fields:
                property_keys.append(field)
    for key in property_keys:
        #try:
        if form.cleaned_data[key] or form.cleaned_data[key] == 0:
            pre_value = node.get_property(key, '')
            if pre_value != form.cleaned_data[key]:
                with nc.neo4jdb.transaction:
                    node[key] = form.cleaned_data[key]
                if key == 'name':
                    nh.node_name = form.cleaned_data[key]
                nh.modifier = user
                nh.save()
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
                update_node_search_index(nc.neo4jdb, node)
        elif not form.cleaned_data[key] and key in node.propertyKeys:
            if key != 'name': # Never delete name
                pre_value = node.get_property(key, '')
                if key in django_settings.SEARCH_INDEX_KEYS:
                    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
                    nc.del_index_item(nc.neo4jdb, index, node, key)
                with nc.neo4jdb.transaction:
                    del node[key]
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
    return True

def dict_update_node(user, node, dictionary, property_keys):
    """
    Takes a node, a dict and the property keys that should be used to fill the
    node.
    Returns True if all non-empty properties where added.
    """
    nh = NodeHandle.objects.get(pk=node['handle_id'])
    for key in property_keys:
        if dictionary.get(key, None) or dictionary.get(key, None) == 0:
            pre_value = node.get_property(key, '')
            if pre_value != dictionary[key]:
                with nc.neo4jdb.transaction:
                    node[key] = dictionary[key]
                if key == 'name':
                    nh.node_name = dictionary[key]
                nh.modifier = user
                nh.save()
                activitylog.update_node_property(user, nh, key, pre_value, dictionary[key])
                update_node_search_index(nc.neo4jdb, node)
        elif dictionary.get(key, None) == '' and key in node.propertyKeys:
            if key != 'name':  # Never delete name
                pre_value = node.get_property(key, '')
                if key in django_settings.SEARCH_INDEX_KEYS:
                    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
                    nc.del_index_item(nc.neo4jdb, index, node, key)
                with nc.neo4jdb.transaction:
                    del node[key]
                activitylog.update_node_property(user, nh, key, pre_value, dictionary[key])
    return True


def dict_update_relationship(user, rel, dictionary, property_keys):
    """
    Takes a relationship, a dict and the property keys that should be used to fill the
    node.
    Returns True if all non-empty properties where added.
    """
    for key in property_keys:
        if dictionary.get(key, None) or dictionary.get(key, None) == 0:
            pre_value = rel.get_property(key, '')
            if pre_value != dictionary[key]:
                with nc.neo4jdb.transaction:
                    rel[key] = dictionary[key]
                activitylog.update_relationship_property(user, rel, key, pre_value, dictionary[key])
                update_relationship_search_index(nc.neo4jdb, rel)
        elif dictionary.get(key, None) == '' and key in rel.propertyKeys:
            pre_value = rel.get_property(key, '')
            if key in django_settings.SEARCH_INDEX_KEYS:
                index = nc.get_relationship_index(nc.neo4jdb, nc.search_index_name())
                nc.del_index_item(nc.neo4jdb, index, rel, key)
            with nc.neo4jdb.transaction:
                del rel[key]
            activitylog.update_relationship_property(user, rel, key, pre_value, dictionary[key])
    return True


def form_to_generic_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    node_type = slug_to_node_type(slug, create=True)
    node_handle = NodeHandle(node_name=node_name,
        node_type=node_type,
        node_meta_type=node_meta_type,
        modifier=request.user, creator=request.user)
    node_handle.save()
    activitylog.create_node(request.user, node_handle)
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
        activitylog.create_node(request.user, node_handle)
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
    does not exist we return None.
    """
    try:
        ts = item.get_property('noclook_last_seen', None)  # ex. 2011-11-01T14:37:13.713434
        dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f')
    except TypeError:
        return None
    return dt


def neo4j_data_age(item, max_data_age=None):
    """
    Checks the noclook_last_seen property against datetime.datetime.now() and
    if the difference is greater than max_data_age (hours)
    (django_settings.NEO4J_MAX_DATA_AGE will be used if max_data_age is not specified)
    and the noclook_auto_manage is true the data is said to be expired.
    Returns noclook_last_seen as a datetime and a "expired" boolean.
    """
    if not max_data_age:
        max_data_age = django_settings.NEO4J_MAX_DATA_AGE
    max_age = timedelta(hours=int(max_data_age))
    now = datetime.now()
    last_seen = isots_to_dt(item)
    expired = False
    if last_seen and (now-last_seen) > max_age and item.get_property('noclook_auto_manage', False):
        expired = True
    return last_seen, expired


def neo4j_report_age(item, old, very_old):
    """
    Checks the noclook_last_seen property and returns the items age based on a arbitrarily chosen
    time spans.

    :param item: neo4j object
    :param old: integer after how many days the item is old
    :param very_old: integer after how many days the item is very old
    :return: string current|old|very_old
    """
    today = datetime.today()
    two_weeks = today - timedelta(days=old)
    month = today - timedelta(days=very_old)
    last_seen, expired = neo4j_data_age(item)
    if two_weeks >= last_seen > month:
        return 'old'
    elif last_seen <= month:
        return 'very_old'
    else:
        return 'current'

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

def dicts_to_csv(dict_list, header=None):
    """
    Takes a list of dicts and returns a comma separated file with all dict keys
    and their values.
    """
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=result.csv; charset=utf-8;'
    writer = UnicodeWriter(response, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
    if not header:
        key_set = set()
        for item in dict_list:
            key_set.update(item.keys())
        key_set = sorted(key_set)
    else:
        key_set = header
    writer.writerow(key_set) # Line collection with header
    for item in dict_list:
        line = []
        for key in key_set:
            try:
                line.append('%s' % normalize_whitespace(item[key]))
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


def dicts_to_xls(dict_list, header, sheet_name):
    """
    Takes a list of dicts and returns an Excel Workbook object of all dicts key value pair in header.

    :param dict_list: List of dicts
    :param header: List of unique strings
    :param sheet_name: String
    :return: xlwt.Workbook
    """
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(sheet_name)
    # Write header
    for i in range(0, len(header)):
        ws.write(0, i, header[i])
    # Write body
    for i in range(0, len(dict_list)):
        for j in range(0, len(header)):
            try:
                ws.write(i+1, j, normalize_whitespace(dict_list[i][header[j]]))
            except KeyError:
                ws.write(i+1, j, unicode(''))
    return wb


def dicts_to_xls_response(dict_list, header=None):
    """
    Takes a list of dicts and returns a response object with and Excel file.
    """
    # Create the HttpResponse object with the appropriate Excel header.
    response = HttpResponse(mimetype='application/excel')
    response['Content-Disposition'] = 'attachment; filename=result.xls;'

    if not header:
        key_set = set()
        for item in dict_list:
            key_set.update(item.keys())
        key_set = sorted(key_set)
    else:
        key_set = header
    wb = dicts_to_xls(dict_list, key_set, 'NOCLook result')
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


def create_email(subject, body, to, cc=None, bcc=None, attachement=None, filename=None, mimetype=None):
    """
    :param subject: String
    :param body: String
    :param to: List
    :param attachement: File
    :param filename: String
    :param mimetype: String
    :return: EmailMessage
    """
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=None,  # Use DEFAULT_FROM_EMAIL in settings.py.
        to=to,
        cc=cc,
        bcc=bcc
    )
    if attachement and filename and mimetype:
        email.attach(filename, attachement, mimetype)
    return email

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


def get_history(nh):
    """
    :param nh: NodeHandle
    :return: List of ActStream actions
    """
    history = list(action_object_stream(nh)) + list(target_stream(nh))
    return sorted(history, key=lambda action: action.timestamp, reverse=True)

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

def part_of(node):
    """
    Returns the node place and the places parent, if any.
    """
    q = '''
        START node=node({id})
        MATCH node-[loc_rel:Part_of]->loc<-[?:Has*1..]-parent
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
        MATCH node-[r0:Connected_to]->port<-[?:Has*1..10]-end-[?:Located_in]->location<-[?:Has]-site
        RETURN node, r0, port, end, location, site
        '''
    hits = nc.neo4jdb.query(q, id=cable.getId())
    for hit in hits:
        connected.append({'cable': hit['node'], 'rel': hit['r0'], 
                          'port': hit['port'], 'end': hit['end'],
                          'location': hit['location'], 'site': hit['site']})
    connected = sorted(connected, key=itemgetter('port')) 
    return connected

def get_connected_equipment(equipment):
    """
    Get all the nodes Has relationships and what they are connected to.
    """
    q = '''
        START node=node({id})
        MATCH node-[:Has*1..]->porta<-[r0?:Connected_to]-cable-[r1:Connected_to]->portb<-[?:Has*1..]-end-[?:Located_in]-location<-[?:Has]-site
        RETURN node,porta,r0,cable,r1,portb,end,location,site
        '''
    return nc.neo4jdb.query(q, id=equipment.getId())

def get_depends_on_equipment(equipment):
    """
    Get all the nodes Has or Depends_on relationships.
    """
    q = '''
        START node=node({id})
        MATCH node-[?:Has*1..]->port<-[:Depends_on|Part_of]-port_logical, node<-[?:Depends_on|Part_of]-direct_logical
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


def get_depends_on_port(port):
    """
    :param port: Neo4j node
    :return: Cypher query iterator
    """
    q = '''
        START node=node({id})
        MATCH node<-[:Connected_to]-cable-[:Connected_to]->()
        WITH cable
        MATCH cable-[:Connected_to*1..]->port<-[:Depends_on|Part_of]-port_logical
        RETURN DISTINCT port_logical
        '''
    return nc.neo4jdb.query(q, id=port.getId())


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
        MATCH node<-[:Part_of]-unit
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


def get_dependent_on_cable_as_types(cable):
    """
    Get top services that depends on the supplied cable and the services dependencies.
    :param cable: Neo4j node
    :return: neo4j.cypher.pycompat.WrappedMap
    """
    q = '''
        START node=node({id})
        MATCH node-[:Connected_to]->equip
        WITH equip
        MATCH equip<-[:Depends_on*1..]-dep
        WITH distinct dep
        WITH collect(dep) as deps, filter(n in collect(dep) : n.node_type = "Service") as services
        WITH deps, services, filter(n in deps : n.node_type = "Optical Path") as paths
        WITH deps, services, paths, filter(n in deps : n.node_type = "Optical Multiplex Section") as oms
        WITH deps, services, paths, oms, filter(n in deps : n.node_type = "Optical Link") as links
        RETURN services, paths, oms, links
        '''
    for hit in nc.neo4jdb.query(q, id=cable.getId()):
        return hit


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


def get_dependencies_as_types(node):
    """
    Return the nodes dependencies sorted as node types.
    :param node: Neo4j node
    :return: neo4j.cypher.pycompat.WrappedMap
    """
    q = """
        START node = node({id})
        MATCH node-[:Depends_on*1..]->dep
        WITH collect(dep) as deps, filter(n in collect(dep) : n.node_type = "Service") as services
        WITH deps, services, filter(n in deps : n.node_type = "Optical Path") as paths
        WITH deps, services, paths, filter(n in deps : n.node_type = "Optical Multiplex Section") as oms
        WITH deps, services, paths, oms, filter(n in deps : n.node_type = "Optical Link") as links
        RETURN services, paths, oms, links
        """
    for hit in nc.neo4jdb.query(q, id=node.getId()):
        return hit


def get_dependent_as_types(node):
    """
    Return the nodes dependencies sorted as node types.
    :param node: Neo4j node
    :return: neo4j.cypher.pycompat.WrappedMap
    """
    q = """
        START node = node({id})
        MATCH node<-[:Depends_on*1..]-dep
        WITH collect(dep) as deps, filter(n in collect(dep) : n.node_type = "Service") as services
        WITH deps, services, filter(n in deps : n.node_type = "Optical Path") as paths
        WITH deps, services, paths, filter(n in deps : n.node_type = "Optical Multiplex Section") as oms
        WITH deps, services, paths, oms, filter(n in deps : n.node_type = "Optical Link") as links
        RETURN services, paths, oms, links
        """
    for hit in nc.neo4jdb.query(q, id=node.getId()):
        return hit


def get_unit(port, unit_name):
    """
    Parents should be uniquely named and ports should be uniquely named for each parent.
    :param port: Neo4j node
    :param unit_name: String
    :return unit: Neo4j node
    """
    q = '''
        START port=node({port})
        MATCH port<-[Part_of]-unit
        WHERE unit.name = {unit}
        RETURN unit
        '''
    hits = nc.neo4jdb.query(q, port=port.getId(), unit=str(unit_name))
    try:
        unit = [hit['unit'] for hit in hits][0]
    except IndexError:
        unit = None
    return unit


def create_unit(parent_node, unit_name, creator):
    """
    Creates a port with the supplied parent.
    :param parent_node: Neo4j node
    :param unit_name: String
    :param creator: Django user
    :return: Neo4j node
    """
    type_unit = NodeType.objects.get(type="Unit")
    nh = NodeHandle.objects.create(
        node_name=unit_name,
        node_type=type_unit,
        node_meta_type='Logical',
        modifier=creator, creator=creator
    )
    activitylog.create_node(creator, nh)
    unit_node = nh.get_node()
    rel = nc.create_relationship(nc.neo4jdb, unit_node, parent_node, 'Part_of')
    set_noclook_auto_manage(nc.neo4jdb, rel, True)
    activitylog.create_relationship(creator, rel)
    return unit_node


def get_ports(equipment):
    """
    :param equipment: neo4j node
    :return: list of neo4j nodes and their relationship towards equipment
    """
    q = '''
        START parent=node({id})
        MATCH parent-[r:Has*1..]->port
        WHERE port.node_type = "Port"
        RETURN port,last(r) as rel
        ORDER BY port.name
        '''
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


def create_port(parent_node, port_name, creator):
    """
    Creates a port with the supplied parent.
    :param parent_node: Neo4j node
    :param port_name: String
    :param creator: Django user
    :return: Neo4j node
    """
    type_port = NodeType.objects.get(type="Port")
    nh = NodeHandle.objects.create(
        node_name=port_name,
        node_type=type_port,
        node_meta_type='Physical',
        modifier=creator, creator=creator
    )
    activitylog.create_node(creator, nh)
    port_node = nh.get_node()
    place_child_in_parent(creator, port_node, parent_node.getId())
    return port_node


def logical_to_physical(user, nh, node):
    with nc.neo4jdb.transaction:
        # Make the node physical
        nc.delete_relationship(nc.neo4jdb, iter2list(node.Contains.incoming)[0])
        physical = nc.get_meta_node(nc.neo4jdb, 'physical')
        nc._create_relationship(nc.neo4jdb, physical, node, 'Contains')
        nh.node_meta_type = 'physical'
        nh.save()
        # Convert Uses relationships to Owns.
        user_relationships = node.Uses.incoming
        for rel in user_relationships:
            set_owner(user, node, rel.start.id)
            activitylog.delete_relationship(user, rel)
            nc.delete_relationship(nc.neo4jdb, rel)
    return nh, node


def place_physical_in_location(user, nh, node, location_id):
    """
    Places a physical node in a rack or on a site. Also converts it to a
    physical node if it still is a logical one.
    """
    # Check if the node is logical
    meta_type = nc.get_node_meta_type(node)
    if meta_type == 'logical':
        nh, node = logical_to_physical(user, nh, node)
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
        rel = nc.create_relationship(nc.neo4jdb, node,
            location_node, 'Located_in')
        activitylog.create_relationship(user, rel)
    return nh, node

def place_child_in_parent(user, node, parent_id):
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
            activitylog.delete_relationship(user, rel)
            nc.delete_relationship(nc.neo4jdb, rel)
        rel = nc.create_relationship(nc.neo4jdb, parent_node,
            node, 'Has')
        activitylog.create_relationship(user, rel)
    return node

def connect_physical(user, node, other_node_id):
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
        rel = nc.create_relationship(nc.neo4jdb, node, other_node,
            'Connected_to')
        activitylog.create_relationship(user, rel)
    return node

def set_owner(user, node, owner_node_id):
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
        rel = nc.create_relationship(nc.neo4jdb, owner_node, node,
            'Owns')
        activitylog.create_relationship(user, rel)
    return node

def set_user(user, node, user_node_id):
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
        rel = nc.create_relationship(nc.neo4jdb, user_node, node,
            'Uses')
        activitylog.create_relationship(user, rel)
    return node

def set_provider(user, node, provider_node_id):
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
            activitylog.delete_relationship(user, rel)
            nc.delete_relationship(nc.neo4jdb, rel)
        rel = nc.create_relationship(nc.neo4jdb, provider_node, node,
            'Provides')
        activitylog.create_relationship(user, rel)
    return node

def set_depends_on(user, node, depends_on_node_id):
    """
    Creates or updates an Depends_on relationship between the node and the
    owner node.
    Returns the node.
    """
    depends_on_node = nc.get_node_by_id(nc.neo4jdb,  depends_on_node_id)
    rel_exist = nc.get_relationships(node, depends_on_node, 'Depends_on')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        rel = nc.create_relationship(nc.neo4jdb, node, depends_on_node,
            'Depends_on')
        activitylog.create_relationship(user, rel)
    return node

def set_responsible_for(user, node, responsible_for_node_id):
    """
    Creates or updates an Responsible_for relationship between the node and the
    site owner node.
    Returns the node.
    """
    responsible_for_node = nc.get_node_by_id(nc.neo4jdb, responsible_for_node_id)
    rel_exist = nc.get_relationships(responsible_for_node, node, 'Responsible_for')
    # If the location is the same as before just update relationship
    # properties
    if rel_exist:
        # TODO: Change properties here
        #location_rel = rel_exist[0]
        #with nc.neo4jdb.transaction:
        pass
    else:
        rel = nc.create_relationship(nc.neo4jdb, responsible_for_node, node, 'Responsible_for')
        activitylog.create_relationship(user, rel)
    return node


def get_host_backup(host):
    """
    :param host: neo4j node
    :return: String

    Return a string that expresses the current backup solution used for the host or 'No'.
    """
    backup = host.get_property('backup', 'No')
    if backup == 'No':
        q = """
            START host=node({id})
            MATCH host<-[r:Depends_on]-dep
            WHERE dep.name = 'vnetd'
            RETURN r
            """
        for hit in nc.neo4jdb.query(q, id=host.getId()):
            last_seen, expired = neo4j_data_age(hit['r'])
            if not expired:
                backup = 'netbackup'
    return backup


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

def is_free_unique_id(unique_id_collection, unique_id):
    """
    Checks if a Unique ID is unused or reserved.
    :param unique_id_collection: Instance of a UniqueId subclass.
    :param unique_id: String
    :return: Boolean
    """
    try:
        obj = unique_id_collection.objects.get(unique_id=unique_id)
        if obj.reserved:
            return True
    except ObjectDoesNotExist:
        return True
    return False

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