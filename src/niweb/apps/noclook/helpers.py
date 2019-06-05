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
from django.utils import six
import csv
import xlwt
import re
import os
from neo4j.v1.types import Node

from .models import NodeHandle, NodeType
from . import activitylog
import norduniclient as nc
from norduniclient.exceptions import UniqueNodeError, NodeNotFound

# File upload
from django.core.files.uploadedfile import SimpleUploadedFile
from attachments.models import Attachment
from django.contrib.contenttypes.models import ContentType


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
    node_model = nc.get_node_model(nc.graphdb.manager, node_handle.handle_id)
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
            activitylog.delete_node(user, nh)
        except (NodeNotFound, AttributeError):
            pass
        nh.delete()
    except ObjectDoesNotExist:
        pass
    return True


def delete_relationship(user, relationship_id):
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
    activitylog.delete_relationship(user, relationship)
    relationship.delete()
    return True


def get_provider_id(provider_name):
    """
    Get a node id to be able to provide a forms initial with a default provider.
    :provider_name String Provider name
    :return String Provider node id or empty string
    """
    providers = nc.get_nodes_by_value(nc.graphdb.manager, provider_name, 'name', 'Provider')
    try:
        provider_id = str(next(providers).get('handle_id', ''))
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
                   'services_checked', 'relationship_responsible_for', 'relationship_connected_to']
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
                # Handle dates
                if hasattr(form.cleaned_data[key], 'isoformat'):
                    node.data[key] = form.cleaned_data[key].isoformat()

                if key == 'name':
                    nh.node_name = form.cleaned_data[key]
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
        elif form.cleaned_data.get(key, None) == '' and key in node.data.keys():
            if key != 'name':  # Never delete name
                pre_value = node.data.get(key, '')
                del node.data[key]
                activitylog.update_node_property(user, nh, key, pre_value, form.cleaned_data[key])
    nc.set_node_properties(nc.graphdb.manager, node.handle_id, node.data)
    return True


def dict_update_node(user, handle_id, properties, keys=None, filtered_keys=list()):
    nh, node = get_nh_node(handle_id)
    if not keys:
        keys = properties.keys()
    for key in keys:
        if key in filtered_keys:
            continue
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
    nc.set_node_properties(nc.graphdb.manager, handle_id, node.data)
    return True


def dict_update_relationship(user, relationship_id, properties, keys=None):
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    nc.set_relationship_properties(nc.graphdb.manager, relationship_id, relationship.data)
    return True


def form_to_generic_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    return get_generic_node_handle(request.user, node_name, slug, node_meta_type)

def get_generic_node_handle(user, node_name, slug, node_meta_type):
    node_type = slug_to_node_type(slug, create=True)
    node_handle = NodeHandle(node_name=node_name, node_type=node_type, node_meta_type=node_meta_type,
                             modifier=user, creator=user)
    node_handle.save()
    activitylog.create_node(user, node_handle)
    set_noclook_auto_manage(node_handle.get_node(), False)
    return node_handle



def form_to_unique_node_handle(request, form, slug, node_meta_type):
    node_name = form.cleaned_data['name']
    return create_unique_node_handle(request.user, node_name, slug, node_meta_type)

def create_unique_node_handle(user, node_name, slug, node_meta_type):
    node_type = slug_to_node_type(slug, create=True)
    try:
        node_handle = NodeHandle.objects.get(node_name__iexact=node_name, node_type=node_type)
        raise UniqueNodeError(node_name, node_handle.handle_id, node_type)
    except NodeHandle.DoesNotExist:
        node_handle = NodeHandle.objects.create(node_name=node_name, node_type=node_type, node_meta_type=node_meta_type,
                                                modifier=user, creator=user)
        activitylog.create_node(user, node_handle)
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
        node = nc.get_node_model(nc.graphdb.manager, item.handle_id)
        node.data.update(auto_manage_data)
        nc.set_node_properties(nc.graphdb.manager, node.handle_id, node.data)
    elif isinstance(item, nc.models.BaseRelationshipModel):
        relationship = nc.get_relationship_model(nc.graphdb.manager, item.id)
        relationship.data.update(auto_manage_data)
        nc.set_relationship_properties(nc.graphdb.manager, relationship.id, relationship.data)
    

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
            node = nc.get_node_model(nc.graphdb.manager, item.handle_id)
            node.data.update(auto_manage_data)
            nc.set_node_properties(nc.graphdb.manager, node.handle_id, node.data)
        elif isinstance(item, nc.models.BaseRelationshipModel):
            relationship = nc.get_relationship_model(nc.graphdb.manager, item.id)
            relationship.data.update(auto_manage_data)
            nc.set_relationship_properties(nc.graphdb.manager, relationship.id, relationship.data)


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
    writer = csv.writer(response, dialect=csv.excel, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
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
                ws.write(i+1, j, u'')
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
    model = nc.get_node_model(nc.graphdb.manager, handle_id)
    for t in model.labels:
        try:
            return NodeType.objects.get(type=t.replace('_', ' ')).type
        except NodeType.DoesNotExist:
            pass


def labels_to_node_type(labels):
    for label in labels:
        if label in nc.core.META_TYPES or label == 'Node':
            continue
        return label.replace('_', ' ')


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
    type_port = slug_to_node_type("port", create=True)
    nh = NodeHandle.objects.create(
        node_name=port_name,
        node_type=type_port,
        node_meta_type='Physical',
        modifier=creator, creator=creator
    )
    activitylog.create_node(creator, nh)
    set_has(creator, parent_node, nh.handle_id)
    return nh.get_node()

def bulk_create_ports(parent_node, creator, num_ports=0, port_type='', offset=1, prefix='', bundled=False, no_ports=False):
    offset = int(offset or 1)
    num_ports = int(num_ports or 0)
    end_port = num_ports+offset
    if bundled:
        step=2
    else:
        step=1
    for p in range(offset, end_port, step):
        if bundled:
            node_name = u'{}{}+{}'.format(prefix,p,p+1)
        else:
            node_name = u'{}{}'.format(prefix,p)
        port_handle = get_generic_node_handle(creator, node_name, 'port', 'Physical')
        dict_update_node(creator, port_handle.handle_id, {'port_type': port_type})
        #set parent relation
        set_has(creator, parent_node, port_handle.handle_id)


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
        relationship = nc.get_relationship_model(nc.graphdb.manager, item.get('relationship_id'))
        set_owner(user, physical_node, relationship.start)
        activitylog.delete_relationship(user, relationship)
        relationship.delete()
    # Remove Depends_on relationships
    logical = physical_node.get_dependencies()
    for item in logical.get('Depends_on', []):
        relationship = nc.get_relationship_model(nc.graphdb.manager, item.get('relationship_id'))
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
        relationship = nc.get_relationship_model(nc.graphdb.manager, item.get('relationship_id'))
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
    created = result.get('Located_in')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def remove_locations(user, node):
    # Remove Located_in relationships
    location = node.get_location()
    for item in location.get('Located_in', []):
        relationship = nc.get_relationship_model(nc.graphdb.manager, item.get('relationship_id'))
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
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
            WHERE r.state IN ['open', 'open|filtered']
            RETURN r
            """
        for hit in nc.query_to_list(nc.graphdb.manager, q, handle_id=host.handle_id):
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
        WHERE exists(r.rogue_port)
        RETURN collect(id(r)) as ids
        """
    result = nc.query_to_dict(nc.graphdb.manager, q, handle_id=handle_id)
    properties = {'rogue_port': ''}
    for relationship_id in result['ids']:
        dict_update_relationship(user, relationship_id, properties, properties.keys())
    return True


def find_recursive(key, target):
    if type(target) in (list, tuple):
        for d in target:
            for result in find_recursive(key, d):
                yield result
    elif isinstance(target, dict) or isinstance(target, Node):
        if isinstance(target, Node):
            target = target.properties
        for k, v in target.items():
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

def app_enabled(appname):
    return appname in django_settings.INSTALLED_APPS


# Simple sorting that handles numbers such as 1-1 1-2 1-11
convert = lambda text: int(text) if text.isdigit() else text
alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
def sort_nicely(l, key=None):
    if key:
        l.sort(key=lambda x: alphanum_key(x.get(key)))
    else:
        l.sort(key=alphanum_key)

def attach_as_file(handle_id, name, content, user, overwrite=False):
    """
        Attach a file to a handle_id.
        - handle_id the id of the node to attach a file to.
        - name the name of the file
        - content the content of the file (e.g. a string)
        - user the user doing the attach
        - overwrite should the file be overwritten if it exists. (Default: False)

        All files are stored in {root}/niweb/media/attachments, and the metadata is attached in the django db.
    """
    nh = NodeHandle.objects.get(pk=handle_id)
    _file = SimpleUploadedFile(name, content.encode('utf-8'), content_type="text/plain")
    if overwrite:
        attachment = Attachment.objects.filter(object_id=handle_id, attachment_file__endswith=name).first()
        if attachment:
            attachment.attachment_file.delete()
    if not attachment:
        attachment = Attachment()
    attachment.content_type = ContentType.objects.get_for_model(nh)
    attachment.object_id = handle_id
    attachment.creator = user
    attachment.attachment_file = _file
    return attachment.save()

def find_attachments(handle_id, name=None):
    attachments = Attachment.objects.filter(object_id=handle_id)
    if name:
        attachments.filter(attachment_file__endswith=name)
    return attachments

def attachment_content(attachment):
    if not attachment:
        return ""
    file_name = os.path.join(django_settings.MEDIA_ROOT, attachment.attachment_file.name)
    with open(file_name, 'r') as f:
        content = f.read()
    return content

def set_parent_of(user, node, child_org_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param child_org_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.set_child(child_org_id)
    relationship_id = result.get('Parent_of')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
    created = result.get('Parent_of')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created

def set_uses_a(user, node, procedure_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param procedure_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.add_procedure(procedure_id)
    relationship_id = result.get('Uses_a')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
    created = result.get('Uses_a')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created

def set_works_for(user, node, organization_id, role_name):
    """
    :param user: Django user
    :param node: norduniclient model
    :param organization_id: unique id
    :param role_name: string for role name
    :return: norduniclient model, boolean
    """
    from pprint import pprint
    contact_id = node.handle_id
    relationship = nc.models.RoleRelationship.link_contact_organization(contact_id, organization_id, role_name)

    if not relationship:
        relationship = RoleRelationship()
        relationship.load_from_nodes(contact_id, organization_id)

    node = node.reload()
    created = node.outgoing.get('Works_for')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created

def set_member_of(user, node, group_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param group_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.add_group(group_id)
    relationship_id = result.get('Member_of')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
    created = result.get('Member_of')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)
    return relationship, created


def set_of_member(user, node, contact_id):
    """
    :param user: Django user
    :param node: norduniclient model
    :param contact_id: unique id
    :return: norduniclient model, boolean
    """
    result = node.add_member(contact_id)
    relationship_id = result.get('Member_of')[0].get('relationship_id')
    relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
    created = result.get('Member_of')[0].get('created')

    if created:
        activitylog.create_relationship(user, relationship)

    return relationship, created


def link_contact_role_for_organization(user, node, contact_handle_id, role_name):
    """
    :param user: Django user
    :param node: norduniclient contact model
    :param contact_handle_id: contact's handle_id
    :param role_name: role name
    :return: contact
    """
    if six.PY2:
        role = role.encode('utf-8')

    relationship = nc.models.RoleRelationship.link_contact_organization(
        contact_handle_id,
        node.handle_id,
        role_name
    )

    if not relationship:
        relationship = RoleRelationship()
        relationship.load_from_nodes(contact_id, organization_id)

    node = node.reload()
    created = node.incoming.get('Works_for')[0].get('created')
    if created:
        activitylog.create_relationship(user, relationship)

    contact = NodeHandle.objects.get(handle_id=contact_handle_id)

    return contact


def create_contact_role_for_organization(user, node, contact_name, role_name):
    """
    :param user: Django user
    :param node: norduniclient organization model
    :param contact_name: full name of the contact
    :return: contact, role: New objects if they're not present in the db
    """
    contact_type = NodeType.objects.get(type='Contact')

    # convert string if necesary
    if six.PY2:
        contact_name = contact_name.encode('utf-8')
        role_name = role_name.encode('utf-8')

    first_name, last_name = contact_name.split(' ')

    # create or get contact
    contact, created_contact = NodeHandle.objects.get_or_create(
        node_name=contact_name,
        node_type=contact_type,
        node_meta_type='Relation',
        creator=user,
        modifier=user,
    )

    if created_contact:
        activitylog.create_node(user, contact)
        contact.get_node().add_property('first_name', first_name)
        contact.get_node().add_property('last_name', last_name)

    relationship = nc.models.RoleRelationship.link_contact_organization(
        contact.handle_id,
        node.handle_id,
        role_name
    )

    if not relationship:
        relationship = RoleRelationship()
        relationship.load_from_nodes(contact_id, organization_id)

    node = node.reload()

    created = False
    for relation in node.relationships.get('Works_for'):
        if relation['node'].handle_id == contact.handle_id:
            created = relation.get('created')
    
    if created:
        activitylog.create_relationship(user, relationship)


def get_contact_for_orgrole(organization_id, role_name):
    """
    :param organization_id: Organization's handle_id
    :param role_name: Role name
    """
    q = """
    MATCH (c:Contact)-[:Works_for {{ name: '{role_name}'}}]->(o:Organization)
    WHERE o.handle_id = {organization_id}
    RETURN c.handle_id AS handle_id
    """.format(organization_id=organization_id, role_name=role_name)
    d = nc.query_to_dict(nc.graphdb.manager, q)

    if 'handle_id' in d and d['handle_id']:
        contact_handle_id = d['handle_id']
        contact = NodeHandle.objects.get(handle_id=contact_handle_id)

        return contact
