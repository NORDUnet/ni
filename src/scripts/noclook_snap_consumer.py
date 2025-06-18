#!/usr/bin/env python


import utils
import argparse
import logging
from apps.noclook import helpers
from apps.noclook.models import NodeHandle

logger = logging.getLogger('noclook_consumer.snap')

ALLOWED_NODE_TYPE_SET = {'Host'}
NTNX_SERVICE = {
    'dk-ore2-ntnx-4': 'NU-S001347',
    'dk-bal-ntnx-4': 'NU-S001348',
    'dk-ore2-ntnx-5': 'NU-S001349',
    'dk-bal-ntnx-5': 'NU-S001350',
}


def insert_snap(json_list):
    """
    Inserts snap metadata as Hosts.
    """
    user = utils.get_user()
    node_type = "Host"
    for data in json_list:
        # Handle nerds data
        try:
            d = data['host']['snap_metadata']
        except KeyError:
            d = data

        name = d['hostname'].lower()
        logger.info('{} loaded'.format(name))

        meta_type = 'Logical' if d.get('virtual') else 'Physical'

        # find host first hostname, then ip? else create
        node_handle = utils.get_unique_node_handle_by_name(name, node_type, meta_type, ALLOWED_NODE_TYPE_SET)
        # Check it is a host
        if not node_handle or node_handle.node_type.type not in ALLOWED_NODE_TYPE_SET:
            logger.info('{} is not a {} skipping.'.format(name, ALLOWED_NODE_TYPE_SET))
            continue

        # Update host
        node = node_handle.get_node()

        # change from logical to physical if needed?
        if node_handle.node_meta_type == 'Logical' and not d.get('virtual'):
            logger.warning('Converting {} from logical to physical'.format(name))
            helpers.logical_to_physical(user, node.handle_id)

        helpers.update_noclook_auto_manage(node)

        managed_by = 'Puppet' if d.get('managed') else 'Manual'
        responsible = d.get('responsible', 'SEI')

        properties = {
            'os': d['os'],
            'managed_by': managed_by,
            'responsible_group': responsible,
            'description': d.get('description')
        }

        if d.get('network'):
            ipv4 = [n['ip'].split('/')[0] for n in d.get('network', []) if 'ip' in n]
            ipv6 = [n['ipv6'].split('/')[0] for n in d.get('network', []) if 'ipv6' in n]
            # might have a list of ips in service ip
            ipv4_service = []
            ipv6_service = []
            for n in d.get('network', []):
                if 'service_ip' in n:
                    ips = n['service_ip']
                    if not isinstance(ips, list):
                        ips = [ips]
                    ipv4_service = ipv4_service + ips
                if 'service_ipv6' in n:
                    ips = n['service_ipv6']
                    if not isinstance(ips, list):
                        ips = [ips]
                    ipv6_service = ipv6_service + ips

            ipv4_service = [sip.split('/')[0] for sip in ipv4_service]
            ipv6_service = [sip.split('/')[0] for sip in ipv6_service]
            properties['ip_addresses'] = ipv4 + ipv4_service + ipv6 + ipv6_service

        if d.get('managed'):
            # Dont default to False
            properties['syslog'] = True

        if d.get('service_tag'):
            properties['service_tag'] = d.get('service_tag')

        helpers.dict_update_node(user, node.handle_id, properties, properties.keys())

        # service dependencies
        cluster = d.get('target', '').split('/')[0]
        if cluster in NTNX_SERVICE:
            try:
                depends_on_nh = NodeHandle.objects.get(node_name=NTNX_SERVICE[cluster])
                rel, created = helpers.set_depends_on(user, node, depends_on_nh.handle_id)
                if created:
                    # clean up old depends e.g. if host is redeployed to new cluster, if not same delete old
                    # simpler with a cypher maybe?
                    # match(n:Node {handle_id: $handle_id})-[r:Depends_on]->(n2:Node) WHERE n2.name in $service_names return r
                    result = node.get_dependencies()
                    dependencies = result.get('Depends_on') or []
                    del_candidates = set(NTNX_SERVICE.values()).remove(NTNX_SERVICE[cluster])
                    for dep in dependencies:
                        rel = dep.get('relationship')
                        result = [n for n in rel.nodes if n.get('name') in del_candidates]
                        if result:
                            # lets delete this
                            helpers.delete_relationship(user, rel.id)
            except Exception:
                pass
        logger.info('{} has been imported'.format(name))


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    parser.add_argument('--data', help='Path to data instead of configuration file.')
    parser.add_argument('--raw', '-r', help='Consume snap sysconf directly', action='store_true')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    return parser.parse_args()


def main():
    args = cli()

    if args.verbose:
        logger.setLevel(logging.INFO)

    if args.C:
        config = utils.init_config(args.C)
        snap_data_path = config.get('data', 'snap_metadata')
    elif args.data:
        snap_data_path = args.data
    else:
        logger.error("No snap data specified, either supply config or data argument")
        return

    starts_with = 'manifest.json' if args.raw else ''

    if snap_data_path:
        insert_snap(utils.load_json(snap_data_path, starts_with))


if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
