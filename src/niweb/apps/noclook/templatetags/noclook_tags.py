from niweb.apps.noclook.models import NodeType, NodeHandle
from niweb.apps.noclook.helpers import get_node_url, neo4j_data_age, neo4j_report_age, get_location
import norduni_client as nc
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
def noclook_get_ports(item):
    """
    Return port nodes that are either dependencies or connected to item. Also returns the
    ports top parent.
    :param item: Neo4j node
    :return: Cypher ExecutionResult
    """
    q = """
        START node = node({id})
        MATCH node-[r:Connected_to|Depends_on]-port
        WHERE port.node_type = "Port"
        WITH port, r
        MATCH p=port<-[?:Has*1..]-parent
        RETURN port, r, LAST(nodes(p)) as parent
        ORDER BY parent.name
        """
    return nc.neo4jdb.query(q, id=item.getId())


@register.assignment_tag
def noclook_get_location(node):
    return get_location(node)


@register.assignment_tag
def noclook_report_age(item, old, very_old):
    """
    :param item: Neo4j node
    :return: String, current, old, very_old
    """
    return neo4j_report_age(item, old, very_old)


@register.assignment_tag
def noclook_has_rogue_ports(node):
    """
    :param node: Neo4j node
    :return: Boolean
    """
    q = """
        START host=node({id})
        MATCH host<-[r:Depends_on]-host_service
        RETURN count(r.rogue_port?) as c
        """
    hits = int(str([hit['c'] for hit in nc.neo4jdb.query(q, id=node.getId())][0]))  # java.lang.Long
    if hits != 0:
        return True
    return False
