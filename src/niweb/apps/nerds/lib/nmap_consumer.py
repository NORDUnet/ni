from datetime import datetime
from apps.noclook import helpers, activitylog
from . import consumer_util as nlu


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

    #handle services
    insert_services(data['services'], node, external_check)

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

def insert_services(services_dict, host_node, external_check=False):
    #Same dict used for all observed ports
    if external_check:
        # reset all services to be internal, and set the ones found now to public
        nlu.set_all_services_to_not_public(host_node)
    for address in services_dict.keys():
        for protocol in services_dict[address].keys():
            for port, service in services_dict[address][protocol].iteritems():
                if service['state'] != 'closed':
                    relation_properties = {
                        'ip_address': address,
                        'protocol': protocol,
                        'port': port
                    }
                    insert_service(service, relation_properties, host_node, external_check)

def insert_service(service, relation_properties, host_node, external_check):
    service_name = service.get('name', 'unknown')
    service_node_handle = nlu.get_unique_node_handle(service_name, 'Host Service', 'Logical')
    service_node = service_node_handle.get_node()
    helpers.update_noclook_auto_manage(service_node)

    result = host_node.get_host_service(service_node.handle_id, **relation_properties)
    if not result.get('Depends_on'):
        result = host_node.set_host_service(service_node.handle_id, **relation_properties)
    relationship_id = result.get('Depends_on')[0].get('relationship_id')
    relationship = nlu.get_relationship_model(relationship_id) 
    created = result.get('Depends_on')[0].get('created')

    # Set or update relationship properties
    relation_properties.update(service)
    if external_check:
        relation_properties.update({
            'public': True,
            'noclook_last_external_check': datetime.now().isoformat()
        })

    user = nlu.get_user()
    if created:
        activitylog.create_relationship(user, relationship)
        #TODO: log creation
        if host_node.data.get('services_locked', False):
            #TODO: log warning with new port found
            relation_properties['rouge_port'] = True
    else:
        #TODO: log found service
        None
    helpers.update_noclook_auto_manage(relationship)
    #TODO: is properties_keys needed?
    helpers.dict_update_relationship(user, relationship.id, relation_properties)
    #TODO: log processed service


