from django.contrib.auth.models import User
from apps.noclook.models import NodeType, NodeHandle
from apps.noclook import helpers, activitylog
from ipaddr import IPAddress
from lucenequerybuilder import Q
import norduniclient as nc

def get_user(username='noclook'):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        passwd = User.objects.make_random_password(length=30)
        user = User.objects.create_user(username, '', passwd)
    return user

def get_node_type(type_name):
    """
    Returns or creates and returns the NodeType object with the supplied
    name.
    """
    try:
        node_type = NodeType.objects.get(type=type_name)
    except NodeType.DoesNotExist:
        # The NodeType was not found, create one
        from django.template.defaultfilters import slugify
        node_type = NodeType(type=type_name, slug=slugify(type_name))
        node_type.save()
    return node_type

def get_unique_node_handle(node_name, node_type_name, node_meta_type, allowed_node_types=None):
    """
    Takes the arguments needed to create a NodeHandle, if there already
    is a NodeHandle with the same name considered the same one.

    If the allowed_node_types is set the supplied node types will be used for filtering.

    Returns a NodeHandle object.
    """
    node_handle = None
    user = get_user()
    try:
        if not allowed_node_types:
            allowed_node_types = [node_type_name]
        query = NodeHandle.objects.filter(node_type__type__in=allowed_node_types)
        node_handle =  query.get(node_name=node_name)
    except NodeHandle.DoesNotExist:
        node_type = get_node_type(node_type_name)
        defaults = {
            'node_meta_type': node_meta_type,
            'creator': user,
            'modifier': user
        }
        node_handle, created = NodeHandle.objects.get_or_create(node_name=node_name, node_type=node_type, defaults=defaults)
        if created:
            activitylog.create_node(user, node_handle)
    except NodeHandle.MultipleObjectsReturned:
        logger.error("Assumed unique node not unique: {0}".format(node_name))
    return node_handle

def get_relationship_model(relationship_id):
    return nc.get_relationship_model(nc.neo4jdb, relationship_id)

def set_all_services_to_not_public(host):
    """
    Set the hosts relationships to host services public property to false.

    :param host: neo4j node
    :return: None
    """
    q = '''
        MATCH (host {handle_id:{handle_id}})<-[r:Depends_on]-(host_service)
        WHERE has(r.public)
        SET r.public = false
        '''
    with nc.neo4jdb.transaction as t:
        t.execute(q, handle_id=host.handle_id).fetchall()

def address_is_a(addresses, node_types):
    """
    :param addresses: List of IP addresses
    :return: True if the addresses belongs to a host or does not belong to anything
    """
    ip_addresses = [IPAddress(item) for item in addresses]
    for address in addresses:
        q1 = Q('ip_address', '%s*' % address, wildcard=True)
        q2 = Q('ip_addresses', '%s*' % address, wildcard=True)
        lucene_query = unicode(q1 | q2)
        for handle_id in nc.legacy_node_index_search(nc.neo4jdb, lucene_query)['result']:
            node = nc.get_node_model(nc.neo4jdb, handle_id)
            node_addresses = node.data.get('ip_addresses', None) or node.data.get('ip_address', None)
            for addr in node_addresses:
                try:
                    node_address = IPAddress(addr.split('/')[0])
                except ValueError:
                    continue
                if node_address in ip_addresses:
                        if not [l for l in node.labels if l.replace(' ', '_') in node_types]:
                            helpers.update_noclook_auto_manage(node)
                            return False
    return True
