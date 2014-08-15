from django.core.exceptions import ObjectDoesNotExist
from apps.noclook.models import NodeType, NodeHandle
from apps.noclook.helpers import get_node_url, neo4j_data_age, neo4j_report_age
import norduniclient as nc
from datetime import datetime, timedelta
from django import template
register = template.Library()


@register.inclusion_tag('type_menu.html')
def type_menu():
    """
    Returns a list with all wanted NodeType objects for easy menu
    handling.
    Just chain .exclude(type='name') to remove unwanted types.
    """
    types = NodeType.objects.exclude(type='Port').exclude(type='Unit')
    return {'types': types}


@register.simple_tag
def noclook_node_to_url(handle_id):
    """
    Takes a node id as a string and returns the absolute url for a node.
    """
    try:
        return get_node_url(handle_id)
    except ObjectDoesNotExist:
        return ''


@register.assignment_tag
def noclook_node_to_node_handle(node):
    """
    :param node: Neo4j node
    :return node_handle: Django NodeHandle or None
    """
    try:
        node_handle = NodeHandle.objects.get(handle_id = node.getProperty('handle_id', ''))
    except NodeHandle.DoesNotExist:
        return None
    return node_handle


@register.assignment_tag
def noclook_last_seen_to_dt(noclook_last_seen):
    """
    Returns noclook_last_seen property (ex. 2011-11-01T14:37:13.713434) as a
    datetime.datetime. If a datetime cant be made None is returned.
    """
    try:
        dt = datetime.strptime(noclook_last_seen, '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        dt = None
    return dt


@register.assignment_tag
def timestamp_to_td(seconds):
    """
    Converts a UNIX timestamp to a timedelta object.
    """
    try:
        td = timedelta(seconds=float(seconds))
    except (AttributeError, ValueError):
        td = None
    return td


@register.assignment_tag
def noclook_has_expired(item):
    """
    Returns True if the item has a noclook_last_seen property and it has expired.
    """
    last_seen, expired = neo4j_data_age(item)
    return expired


@register.assignment_tag
def noclook_get_model(handle_id):
    """
    :param handle_id: unique id
    :return: Node model
    """
    try:
        return nc.get_node_model(nc.neo4jdb, handle_id)
    except nc.exceptions.NodeNotFound:
        return ''


@register.simple_tag
def noclook_get_type(handle_id):
    model = nc.get_node_model(nc.neo4jdb, handle_id)
    for t in model.labels:
        try:
            return NodeType.objects.get(type=t.replace('_', ' ')).type
        except NodeType.DoesNotExist:
            pass


@register.assignment_tag
def noclook_get_ports(handle_id):
    """
    Return port nodes that are either dependencies or connected to item. Also returns the
    ports top parent.
    :param handle_id: unique id
    :return: list
    """
    return nc.get_node_model(nc.neo4jdb, handle_id).get_ports()


@register.assignment_tag
def noclook_get_location(handle_id):
    return nc.get_node_model(nc.neo4jdb, handle_id).get_location()


@register.assignment_tag
def noclook_report_age(item, old, very_old):
    """
    :param item: Neo4j node
    :return: String, current, old, very_old
    """
    return neo4j_report_age(item, old, very_old)


@register.assignment_tag
def noclook_has_rogue_ports(handle_id):
    """
    :param node:
    :return: Boolean
    """
    q = """
        MATCH (host {handle_id: {handle_id}})<-[r:Depends_on]-()
        RETURN count(r.rogue_port)
        """
    with nc.neo4jdb.read as r:
        count, = r.execute(q, handle_id=handle_id).fetchall()[0]
    if count:
        return True
    return False
