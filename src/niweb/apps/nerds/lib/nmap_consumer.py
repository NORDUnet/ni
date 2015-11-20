from apps.noclook import helpers
import .consumer_util as nlu


# Type of equipment we want to update with this consumer
ALLOWED_NODE_TYPE_SET = {'Host', 'Firewall', 'Switch', 'PDU'}

# TODO: should be in db...
HOST_USERS_MAP = {
    'eduroam.se':       'SUNET',
    'eduid.se':         'SUNET',
    'eid2.se':          'SUNET',
    'funet.fi':         'FUNET',
    'lobber.se':        'SUNET',
    'ndgf.org':         'NDGF',
    'nordu.net':        'NORDUnet',
    'nordunet.tv':      'NORDUnet',
    'nunoc.org':        'NORDUnet',
    'nunoc.se':         'NORDUnet',
    'sunet.se':         'SUNET',
    'rhnet.is':         'RHnet',
    'skolfederation.se':'SUNET',
    'swami.se':         'SUNET',
    'swamid.se':        'SUNET',
    'uninett.no':       'UNINETT',
    'wayf.dk':          'WAYF',
}

def nmap_import(nerds_json, external_check=False):
    """
    Inserts the data loaded from a json file created by
    the nerds producer nmap_services_py.
    """
    item = nerds_json['host']
    data = item['nmap_services_py']
    addresses = data['addresses']

    # find or create node
    name = item['name']
    node_handle =  nlu.get_unique_node_handle(name, "Host", "Logical", ALLOWED_NODE_TYPE_SET)
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

    #handle services
    # TODO: finish it!

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
    host_name = host.data['name']
    domain = extract_domain(host_name)
    stakeholder = HOST_USERS_MAP.get(domain, None)
    relations = host.get_relations()
    if stakeholder and not (relations.get('Uses',None) or relations.get('Owns', None)):
        stakeholder_nh = nlu.get_unique_node_handle(stakeholder, 'Host User', 'Relation')
        if host.meta_type == 'Logical':
            helpers.set_user(user, host, stakeholder_nh.handle_id)
        elif host.meta_type == 'Physical':
            helpers.set_owner(user, host, stakeholder_nh.handle_id)
        #log info
        # logger.info('Host User %s set for host %s', stakeholder, host_name)


def extract_domain(host_name):
    return '.'.join(host_name.split('.')[-2:])
