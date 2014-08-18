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
    from apps.noclook.models import NodeHandle, NordunetUniqueId, UniqueIdGenerator, NodeType
    from apps.noclook import activitylog
except ImportError:
    from apps.noclook.models import NodeHandle, NordunetUniqueId, UniqueIdGenerator, NodeType
    from apps.noclook import activitylog
import norduniclient as nc
from norduniclient.exceptions import UniqueNodeError, NodeNotFound

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


def get_node_url(handle_id):
    """
    Takes a node and returns it's NodeHandles URL or '' if node
    is None.
    """
    try:
        nh = NodeHandle.objects.get(pk=handle_id)
        return nh.get_absolute_url()
    except (TypeError, ValueError):
        # Node is most likely a None value
        return ''


def get_nh_node(handle_id):
    """
    Takes a node handle id and returns the node handle and the node model.
    """
    node_handle = get_object_or_404(NodeHandle, pk=handle_id)
    node_model = nc.get_node_model(nc.neo4jdb, node_handle.handle_id)
    return node_handle, node_model


def delete_node(user, handle_id):
    try:
        nh = NodeHandle.objects.get(pk=handle_id)
        try:
            nh.get_node().delete()
            activitylog.delete_node(user, nh)
        except NodeNotFound:
            pass
        nh.delete()
    except ObjectDoesNotExist:
        pass
    return True


def delete_relationship(user, relationship_id):
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    activitylog.delete_relationship(user, relationship)
    relationship.delete()
    return True


def form_update_node(user, handle_id, form, property_keys=list()):
    """
    Take a node, a form and the property keys that should be used to fill the
    node if the property keys are omitted the form.base_fields will be used.
    Returns True if all non-empty properties where added.
    """
    meta_fields = ['relationship_location', 'relationship_end_a', 'relationship_end_b', 'relationship_parent',
                   'relationship_provider', 'relationship_end_user', 'relationship_customer', 'relationship_depends_on',
                   'relationship_user', 'relationship_owner', 'relationship_located_in', 'relationship_ports',
                   'services_checked']
    nh, node = get_nh_node(handle_id)
    if not property_keys:
        for field in form.base_fields.keys():
            if field not in meta_fields:
                property_keys.append(field)
    for key in property_keys:
        if form.cleaned_data[key] or form.cleaned_data[key] == 0:
            pre_value = node.data.get(key, '')
            if pre_value != form.cleaned_data[key]:
                node.data[key] = form.cleaned_data[key]
                if key == 'name':
                    nh.node_name = form.cleaned_data[key]
                    nh.modifier = user
                    nh.save()
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
        elif not form.cleaned_data[key] and key in node.data.keys():
            if key != 'name':  # Never delete name
                pre_value = node.data.get(key, '')
                del node.data[key]
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
    nc.set_node_properties(nc.neo4jdb, node.handle_id, node.data)
    return True


def dict_update_node(user, handle_id, properties, keys):
    nh, node = get_nh_node(handle_id)
    for key in keys:
        if properties.get(key, None) or properties.get(key, None) == 0:
            pre_value = node.data.get(key, '')
            if pre_value != properties[key]:
                node.data[key] = properties[key]
                if key == 'name':
                    nh.node_name = properties[key]
                    nh.modifier = user
                    nh.save()
                activitylog.update_node_property(user, nh, key, pre_value, properties[key])
        elif properties.get(key, None) == '' and key in node.data.keys():
            if key != 'name':  # Never delete name
                pre_value = node.get(key, '')
                del node.data[key]
                activitylog.update_node_property(user, nh, key, pre_value, properties[key])
    nc.set_node_properties(nc.neo4jdb, handle_id, node.data)
    return True


def dict_update_relationship(user, relationship_id, properties, keys):
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    for key in keys:
        pre_value = relationship.data.get(key, '')
        if properties.get(key, None) or properties.get(key, None) == 0:
            if pre_value != properties[key]:
                relationship.data[key] = properties[key]
                activitylog.update_relationship_property(user, relationship, key, pre_value, properties[key])
        elif properties.get(key, None) == '' and key in relationship.data.keys():
            del relationship.data[key]
            activitylog.update_relationship_property(user, relationship, key, pre_value, properties[key])
    nc.set_relationship_properties(nc.neo4jdb, relationship_id, relationship.data)
    return True


def form_to_generic_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    node_type = slug_to_node_type(slug, create=True)
    node_handle = NodeHandle(node_name=node_name, node_type=node_type, node_meta_type=node_meta_type,
                             modifier=request.user, creator=request.user)
    node_handle.save()
    activitylog.create_node(request.user, node_handle)
    set_noclook_auto_manage(node_handle.get_node(), False)
    return node_handle


def form_to_unique_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    node_type = slug_to_node_type(slug, create=True)
    try:
        node_handle = NodeHandle.objects.get(node_name=node_name, node_type=node_type)
        raise UniqueNodeError(node_name, node_handle.handle_id, node_type)
    except NodeHandle.DoesNotExist:
        node_handle = NodeHandle.objects.create(node_name=node_name, node_type=node_type, node_meta_type=node_meta_type,
                                                modifier=request.user, creator=request.user)
        activitylog.create_node(request.user, node_handle)
        set_noclook_auto_manage(node_handle.get_node(), False)
    return node_handle


def set_noclook_auto_manage(item, auto_manage):
    """
       Sets the node or relationship noclook_auto_manage flag to True or False.
    Also sets the noclook_last_seen flag to now.

    :param item: norduclient model
    :param auto_manage: boolean
    :return: None
    """
    item.data['noclook_auto_manage'] = auto_manage
    item.data['noclook_last_seen'] = datetime.now().isoformat()
    if isinstance(item, nc.models.BaseNodeModel):
        nc.set_node_properties(nc.neo4jdb, item.handle_id, item.data)
    elif isinstance(item, nc.models.BaseRelationshipModel):
        nc.set_relationship_properties(nc.neo4jdb, item.id, item.data)


def update_noclook_auto_manage(item):
    """
    Updates the noclook_auto_manage and noclook_last_seen properties. If 
    noclook_auto_manage is not set, it is set to True.

    :param item: norduclient model
    :return: None
    """
    auto_manage = item.data.get('noclook_auto_manage', None)
    if auto_manage is None:
        item.data['noclook_auto_manage'] = True
    item.data['noclook_last_seen'] = datetime.now().isoformat()
    if isinstance(item, nc.models.BaseNodeModel):
        node = nc.get_node_model(nc.neo4jdb, item.handle_id)
        nc.set_node_properties(nc.neo4jdb, item.handle_id, node.data)
    elif isinstance(item, nc.models.BaseRelationshipModel):
        relationship = nc.get_relationship_model(nc.neo4jdb, item.id)
        nc.set_relationship_properties(nc.neo4jdb, item.id, relationship.data)


def isots_to_dt(data):
    """
    Returns noclook_last_seen property as a datetime.datetime. If the property
    does not exist we return None.
    """
    try:
        ts = data.get('noclook_last_seen', None)
        try:
            dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f')  # ex. 2011-11-01T14:37:13.713434
        except ValueError:
            dt = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')     # ex. 2011-11-01T14:37:13
    except (TypeError, AttributeError):
        return None
    return dt


def neo4j_data_age(data, max_data_age=None):
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
    last_seen = isots_to_dt(data)
    expired = False
    if last_seen and (now-last_seen) > max_age and data.get('noclook_auto_manage', False):
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
    acronym_types = ['odf']  # TODO: Move to sql db
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


def get_place(node):
    """
    Returns the node place and the places parent, if any.
    """
    q = '''
        START node=node({id})
        MATCH node<-[loc_rel:Has]-loc<-[?:Has*1..10]-parent
        RETURN loc,loc_rel,parent
        '''
    return nc.neo4jdb.query(q, id=node.getId())

def part_of(node):
    """
    Returns the node place and the places parent, if any.
    """
    q = '''
        START node=node({id})
        MATCH node-[loc_rel:Part_of]->loc<-[?:Has*1..10]-parent
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
        MATCH node-[:Has*1..10]->porta<-[r0?:Connected_to]-cable-[r1?:Connected_to]->portb<-[?:Has*1..10]-end-[?:Located_in]-location<-[?:Has]-site
        RETURN node,porta,r0,cable,r1,portb,end,location,site
        '''
    return nc.neo4jdb.query(q, id=equipment.getId())

def get_depends_on_equipment(equipment):
    """
    Get all the nodes Has or Depends_on relationships.
    """
    q = '''
        START node=node({id})
        MATCH node-[?:Has*1..10]->port<-[:Depends_on|Part_of]-port_logical, node<-[?:Depends_on|Part_of]-direct_logical
        RETURN port, port_logical, direct_logical
        '''
    return nc.neo4jdb.query(q, id=equipment.getId())

# Alternative get_depends_on_equipment query
#q = '''
#START node=node({id})
#MATCH node-[?:Has*1..10]->port<-[:Depends_on]-port_logical
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
        MATCH cable-[:Connected_to*1..10]->port<-[:Depends_on|Part_of]-port_logical
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
        MATCH dep<-[?:Has*1..10]-parent, dep-[?:Part_of]->parent<-[?:Has*1..10]-grand_parent
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


def get_services_dependent_on_cable(cable):
    """
    Get top services that depends on the supplied cable.
    :param cable: Neo4j node
    :return: Cypher ExecutionResult
    """
    #q = '''
    #    START node=node({id})
    #    MATCH node-[:Connected_to*1..10]-equip
    #    WITH equip
    #    MATCH equip<-[:Depends_on*1..10]-service<-[r?:Depends_on]-()
    #    WHERE (service.node_type = 'Service') AND (r is null)
    #    WITH distinct service
    #    MATCH service<-[:Uses]-user
    #    WHERE user.node_type = 'Customer'
    #    RETURN service, collect(user) as customers
    #    '''
    q = '''
        START node=node({id})
        MATCH node-[:Connected_to*1..20]-equip
        WITH equip
        MATCH equip<-[:Depends_on*1..10]-service
        WHERE (service.node_type = 'Service')
        WITH distinct service
        MATCH service<-[?:Uses]-user
        WITH DISTINCT service, user
        RETURN service, collect(user) as users
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
        MATCH node-[:Connected_to*1..10]-equip
        WITH equip
        MATCH equip<-[:Depends_on*1..10]-dep
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
        MATCH node-[:Has|Depends_on]-()<-[:Depends_on*1..10]-service<-[r?:Depends_on]-()
        WHERE (service.node_type = 'Service') AND (r is null)
        WITH distinct service
        MATCH service<-[:Uses]-user
        WHERE user.node_type = 'Customer'
        RETURN service, collect(user) as customers
        """
    return nc.neo4jdb.query(q, id=equipment.getId())


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
        node_name=str(unit_name),
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


def logical_to_physical(user, handle_id):
    """
    :param user: Django user
    :param handle_id:  unique id
    :return: NodeHandle, norduniclient model
    """
    nh, logical_node = get_nh_node(handle_id)
    # Make the node physical
    meta_type = 'Physical'
    physical_node = logical_node.change_meta_type(meta_type)
    nh.node_meta_type = meta_type
    nh.save()
    # Convert Uses relationships to Owns.
    relations = physical_node.get_relations()
    for item in relations.get('Uses', []):
        relationship = nc.get_relationship_model(nc.neo4jdb, item.get('relationship_id'))
        set_owner(user, physical_node, relationship.start.handle_id)
        activitylog.delete_relationship(user, relationship)
        relationship.delete()
    # Remove Depends_on relationships
    logical = physical_node.get_dependencies()
    for item in logical.get('Depends_on', []):
        relationship = nc.get_relationship_model(nc.neo4jdb, item.get('relationship_id'))
        activitylog.delete_relationship(user, relationship)
        relationship.delete()
    return nh, physical_node


def physical_to_logical(user, handle_id):
    """
    :param user: Django user
    :param handle_id:  unique id
    :return: NodeHandle, norduniclient model
    """
    nh, physical_node = get_nh_node(handle_id)
    # Remove Located_in relationships
    remove_locations(user, physical_node)
    # Make the node logical
    meta_type = 'Logical'
    logical_node = physical_node.change_meta_type(meta_type)
    nh.node_meta_type = meta_type
    nh.save()
    # Convert Owns relationships to Uses.
    relations = logical_node.get_relations()
    for item in relations.get('Owns', []):
        relationship = nc.get_relationship_model(nc.neo4jdb, item.get('relationship_id'))
        set_user(user, logical_node, relationship.start.handle_id)
        activitylog.delete_relationship(user, relationship)
        relationship.delete()
    return nh, logical_node


def set_location(user, node, location_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param location_id: unique id
    :return: norduniclient model, boolean
    """
    # Check that the node is physical, else convert it
    if node.meta_type == 'Logical':
        nh, node = logical_to_physical(user, node.handle_id)
    result = node.set_location(location_id)
    relationship_id = result.get('Located_in')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Located_in')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def remove_locations(user, node):
    # Remove Located_in relationships
    location = node.get_location()
    for item in location.get('Located_in', []):
        relationship = nc.get_relationship_model(nc.neo4jdb, item.get('relationship_id'))
        activitylog.delete_relationship(user, relationship)
        relationship.delete()


def set_owner(user, node, owner_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param owner_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_owner(owner_id)
    relationship_id = result.get('Owns')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Owns')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def set_user(user, node, user_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param user_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_user(user_id)
    relationship_id = result.get('Uses')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    activitylog.create_relationship(user, relationship)
    created = result.get('Uses')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def set_provider(user, node, provider_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param provider_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_provider(provider_id)
    relationship_id = result.get('Provides')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Provides')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def set_depends_on(user, node, dependency_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param dependency_id: unique id
    :return: norduniclient model, boolean
    """
    # Check that the node is physical, else convert it
    if node.meta_type == 'Physical':
        nh, node = physical_to_logical(user, node.handle_id)
    result = node.set_dependency(dependency_id)
    relationship_id = result.get('Depends_on')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Depends_on')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def set_responsible_for(user, node, responsible_for_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param responsible_for_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_responsible_for(responsible_for_id)
    relationship_id = result.get('Responsible_for')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Responsible_for')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def set_part_of(user, node, part_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param part_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_part_of(part_id)
    relationship_id = result.get('Part_of')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Part_of')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def set_has(user, node, has_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param has_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_has(has_id)
    relationship_id = result.get('Has')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Has')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


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


def get_host_backup(host):
    """
    :param host: norduniclient model
    :return: String

    Return a string that expresses the current backup solution used for the host or 'No'.
    """
    backup = host.data.get('backup', 'No')
    if backup == 'No':
        q = """
            MATCH (:Node {handle_id: {handle_id}})<-[r:Depends_on]-(:Node {name: "vnetd"})
            RETURN r
            """
        for hit in nc.query_to_list(nc.neo4jdb, q, handle_id=host.handle_id):
            last_seen, expired = neo4j_data_age(hit)
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


def remove_rogue_service_marker(user, handle_id):
    """
    :param user: Django user
    :param handle_id:  unique id
    :return: True

    Removed the property rogue_port from all Depends_on relationships.
    """
    q = """
        MATCH (host:Node {handle_id:{handle_id}})<-[r:Depends_on]-(host_service:Host_Service)
        WHERE HAS(r.rogue_port)
        RETURN collect(id(r)) as ids
        """
    result = nc.query_to_dict(nc.neo4jdb, q, handle_id=handle_id)
    properties = {'rogue_port': ''}
    for relationship_id in result['ids']:
        dict_update_relationship(user, relationship_id, properties, properties.keys())
    return True


# Unique ID functions
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