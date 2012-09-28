from niweb.apps.noclook.models import NodeType, NodeHandle
from niweb.apps.noclook.helpers import get_node_url
from datetime import datetime
from django import template
register = template.Library()

@register.inclusion_tag('type_menu.html')
def type_menu():
    """
    Returns a list with all wanted NodeType objects for easy menu
    handling.
    Just chain .exclude(type='name') to remove unwanted types.
    """
    types = NodeType.objects.exclude(type='Port')
    return {'types': types}

@register.simple_tag
def noclook_node_to_url(node):
    """
    Takes a node id as a string and returns the absolute url for a node.
    """
    return get_node_url(node)

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