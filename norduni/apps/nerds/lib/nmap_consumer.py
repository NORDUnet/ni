from datetime import datetime
from norduni.apps.noclook import helpers, activitylog
from . import consumer_util as nlu
from norduni.apps.nerds.models import HostUserMap


# Type of equipment we want to update with this consumer
ALLOWED_NODE_TYPE_SET = {'Host', 'Firewall', 'Switch', 'PDU'}

def nmap_import(nerds_json, external_check=False):
    """
    Inserts the data loaded from a json file created by
    the nerds producer nmap_services_py.
    """
    item = nerds_json['host']
    data = item['nmap_services_py']
    addresses = data['addresses']

    if not nlu.address_is_a(addresses, ALLOWED_NODE_TYPE_SET):
        #Address existed but was not a "Host"
        return None
    # find or create node
    name = item['name']
    node_handle =  nlu.get_unique_node_handle(name, "Host", "Logical", ALLOWED_NODE_TYPE_SET)
    if not node_handle or node_handle.node_type.type not in ALLOWED_NODE_TYPE_SET:
        #TODO: log that it is not in ALLOWED_NODE_TYPE_SET
        return None
    node = node_handle.get_node()
    helpers.update_noclook_auto_manage(node)

    properties = {
        'hostnames': data['hostnames'],
        'ip_addresses': addresses
    }

    if 'os' in data:
        if 'class' in data['os']:
            os = data['os']['class']
            properties['os'] = os['osfamily']
            properties['os_version'] = os['osgen']
        elif 'match' in data['os']:
            os = data['os']['match']
            properties['os'] = os['name']

    if 'uptime' in data:
        properties['lastboot'] = data['uptime']['lastboot']
        properties['uptime'] = data['uptime']['seconds']

    properties['backup'] = helpers.get_host_backup(node)

    if not node.data.get('operational_state', None):
        properties['operational_state'] = 'In service'

    user = nlu.get_user()
    helpers.dict_update_node(user, node.handle_id, properties)
    add_host_user(node)

def add_host_user(host):
    """
    Tries to set a Uses or Owns relationship between the Host and a Host User if there are none.
    """
    user = nlu.get_user()
    host_name = host.data['name']
    domain = extract_domain(host_name)
    stakeholder = HostUserMap.objects.filter(domain=domain).first()
    relations = host.get_relations()
    if stakeholder and not (relations.get('Uses',None) or relations.get('Owns', None)):
        stakeholder_nh = nlu.get_unique_node_handle(stakeholder.host_user, 'Host User', 'Relation')
        if host.meta_type == 'Logical':
            helpers.set_user(user, host, stakeholder_nh.handle_id)
        elif host.meta_type == 'Physical':
            helpers.set_owner(user, host, stakeholder_nh.handle_id)
        #log info
        # logger.info('Host User %s set for host %s', stakeholder, host_name)


def extract_domain(host_name):
    return '.'.join(host_name.split('.')[-2:])

