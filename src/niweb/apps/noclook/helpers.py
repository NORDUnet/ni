# -*- coding: utf-8 -*-
"""
Created on Mon Apr  2 11:17:57 2012

@author: lundberg
"""

import socket
from django.conf import settings as django_settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from datetime import datetime, timedelta
from actstream.models import action_object_stream, target_stream
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import csv
import codecs
import cStringIO
import xlwt

from .models import NodeHandle, NodeType
from . import activitylog
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
    try:
        return u' '.join(s.split())
    except AttributeError:
        return s


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
            node = nh.get_node()
            if node.meta_type == 'Physical':
                for has_child in node.get_has().get('Has', []):
                    delete_node(user, has_child.handle_id)
                for part_of_child in node.get_part_of().get('Part_of', []):
                    delete_node(user, part_of_child.handle_id)
            elif node.meta_type == 'Location':
                for has_child in node.get_has().get('Has', []):
                    delete_node(user, has_child.handle_id)
            node.delete()
            activitylog.delete_node(user, nh)
        except (NodeNotFound, AttributeError):
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


def get_provider_id(provider_name):
    """
    Get a node id to be able to provide a forms initial with a default provider.
    :provider_name String Provider name
    :return String Provider node id or empty string
    """
    providers = nc.get_nodes_by_value(nc.neo4jdb, provider_name, 'name', 'Provider')
    try:
        provider_id = str(providers.next().get('handle_id', ''))
    except StopIteration:
        provider_id = ''
    providers.close()
    return provider_id


def form_update_node(user, handle_id, form, property_keys=None):
    """
    Take a node, a form and the property keys that should be used to fill the
    node if the property keys are omitted the form.base_fields will be used.
    Returns True if all non-empty properties where added.
    """
    meta_fields = ['relationship_location', 'relationship_end_a', 'relationship_end_b', 'relationship_parent',
                   'relationship_provider', 'relationship_end_user', 'relationship_customer', 'relationship_depends_on',
                   'relationship_user', 'relationship_owner', 'relationship_located_in', 'relationship_ports',
                   'services_checked', 'relationship_responsible_for']
    nh, node = get_nh_node(handle_id)
    if not property_keys:
        property_keys = []
        for field in form.base_fields.keys():
            if field not in meta_fields:
                property_keys.append(field)
    for key in property_keys:
        if form.cleaned_data.get(key, None) or form.cleaned_data.get(key, None) == 0:
            pre_value = node.data.get(key, '')
            if pre_value != form.cleaned_data[key]:
                node.data[key] = form.cleaned_data[key]
                if key == 'name':
                    nh.node_name = form.cleaned_data[key]
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
        elif form.cleaned_data.get(key, None) == '' and key in node.data.keys():
            if key != 'name':  # Never delete name
                pre_value = node.data.get(key, '')
                del node.data[key]
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
    nc.set_node_properties(nc.neo4jdb, node.handle_id, node.data)
    return True


def dict_update_node(user, handle_id, properties, keys=None):
    nh, node = get_nh_node(handle_id)
    if not keys:
        keys = properties.keys()
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
                pre_value = node.data.get(key, '')
                del node.data[key]
                activitylog.update_node_property(user, nh, key, pre_value, properties[key])
    nc.set_node_properties(nc.neo4jdb, handle_id, node.data)
    return True


def dict_update_relationship(user, relationship_id, properties, keys=None):
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    if not keys:
        keys = properties.keys()
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
    auto_manage_data = {
        'noclook_auto_manage': auto_manage,
        'noclook_last_seen': datetime.now().isoformat()
    }
    if isinstance(item, nc.models.BaseNodeModel):
        node = nc.get_node_model(nc.neo4jdb, item.handle_id)
        node.data.update(auto_manage_data)
        nc.set_node_properties(nc.neo4jdb, node.handle_id, node.data)
    elif isinstance(item, nc.models.BaseRelationshipModel):
        relationship = nc.get_relationship_model(nc.neo4jdb, item.id)
        relationship.data.update(auto_manage_data)
        nc.set_relationship_properties(nc.neo4jdb, relationship.id, relationship.data)
    

def update_noclook_auto_manage(item):
    """
    Updates the noclook_auto_manage and noclook_last_seen properties. If 
    noclook_auto_manage is not set, it is set to True.

    :param item: norduclient model
    :return: None
    """
    auto_manage_data = {}
    auto_manage = item.data.get('noclook_auto_manage', None)
    if auto_manage or auto_manage is None:
        auto_manage_data['noclook_auto_manage'] = True
        auto_manage_data['noclook_last_seen'] = datetime.now().isoformat()
        if isinstance(item, nc.models.BaseNodeModel):
            node = nc.get_node_model(nc.neo4jdb, item.handle_id)
            node.data.update(auto_manage_data)
            nc.set_node_properties(nc.neo4jdb, node.handle_id, node.data)
        elif isinstance(item, nc.models.BaseRelationshipModel):
            relationship = nc.get_relationship_model(nc.neo4jdb, item.id)
            relationship.data.update(auto_manage_data)
            nc.set_relationship_properties(nc.neo4jdb, relationship.id, relationship.data)


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

    :param item: NodeModel data
    :param old: integer after how many days the item is old
    :param very_old: integer after how many days the item is very old
    :return: string current|old|very_old
    """
    today = datetime.today()
    days_old = today - timedelta(days=old)
    days_very_old = today - timedelta(days=very_old)
    last_seen, expired = neo4j_data_age(item)
    if last_seen:
        if days_old >= last_seen > days_very_old:
            return 'old'
        elif last_seen <= days_very_old:
            return 'very_old'
    return 'current'


def dicts_to_csv_response(dict_list, header=None):
    """
    Takes a list of dicts and returns a comma separated file with all dict keys
    and their values.
    """
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
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
        if i % 1000 == 0:
            ws.flush_row_data()
        if i == 65534:
            # Reached the limit of old xls format
            break
    return wb


def dicts_to_xls_response(dict_list, header=None):
    """
    Takes a list of dicts and returns a response object with and Excel file.
    """
    # Create the HttpResponse object with the appropriate Excel header.
    response = HttpResponse(content_type='application/excel')
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


def get_node_type(handle_id):
    model = nc.get_node_model(nc.neo4jdb, handle_id)
    for t in model.labels:
        try:
            return NodeType.objects.get(type=t.replace('_', ' ')).type
        except NodeType.DoesNotExist:
            pass


def slug_to_node_type(slug, create=False):
    """
    Returns or creates and returns the NodeType object from the supplied slug.
    """
    acronym_types = ['odf', 'pdu']  # TODO: Move to sql db
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


def create_unit(parent_node, unit_name, creator):
    """
    Creates a port with the supplied parent.
    :param parent_node: norduniclient model
    :param unit_name: String
    :param creator: Django user
    :return: norduniclient model
    """
    type_unit = NodeType.objects.get(type="Unit")
    nh = NodeHandle.objects.create(
        node_name=str(unit_name),
        node_type=type_unit,
        node_meta_type='Logical',
        modifier=creator, creator=creator
    )
    activitylog.create_node(creator, nh)
    set_part_of(creator, parent_node, nh.handle_id)
    return nh.get_node()


def create_port(parent_node, port_name, creator):
    """
    Creates a port with the supplied parent.
    :param parent_node: norduniclient model
    :param port_name: String
    :param creator: Django user
    :return: norduniclient model
    """
    type_port = NodeType.objects.get(type="Port")
    nh = NodeHandle.objects.create(
        node_name=port_name,
        node_type=type_port,
        node_meta_type='Physical',
        modifier=creator, creator=creator
    )
    activitylog.create_node(creator, nh)
    set_has(creator, parent_node, nh.handle_id)
    return nh.get_node()


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
        set_owner(user, physical_node, relationship.start)
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
        set_user(user, logical_node, relationship.start)
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


def set_connected_to(user, node, has_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param has_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_connected_to(has_id)
    relationship_id = result.get('Connected_to')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.neo4jdb, relationship_id)
    created = result.get('Connected_to')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


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


def find_recursive(key, target):
    if type(target) in (list, tuple):
        for d in target:
            for result in find_recursive(key, d):
                yield result
    elif isinstance(target, dict):
        for k, v in target.iteritems():
            if k == key:
                yield v
            else:
                for result in find_recursive(key, v):
                    yield result
    elif hasattr(target, key):
        yield getattr(target, key)


def get_node_urls(*args):
    ids = []
    for arg in args:
        ids += set(find_recursive("handle_id", arg))
    nodes = NodeHandle.objects.filter(handle_id__in=ids)
    urls = {}
    for n in nodes:
        urls[n.handle_id] = n.get_absolute_url()
    return urls


def paginate(full_list, page=None, per_page=250):
    paginator = Paginator(full_list, per_page, allow_empty_first_page=True)
    try:
        paginated_list = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        paginated_list = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        paginated_list = paginator.page(paginator.num_pages)
    return paginated_list
