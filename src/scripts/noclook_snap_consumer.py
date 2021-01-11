#!/usr/bin/env python


import utils
import argparse
import logging
from apps.noclook import helpers

logger = logging.getLogger('noclook_consumer.snap')

ALLOWED_NODE_TYPE_SET = {'Host'}


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
            ipv4_service = [n['service_ip'].split('/')[0] for n in d.get('network', []) if 'service_ip' in n]
            ipv6 = [n['ipv6'].split('/')[0] for n in d.get('network', []) if 'ipv6' in n]
            ipv6_service = [n['service_ipv6'].split('/')[0] for n in d.get('network', []) if 'service_ipv6' in n]
            properties['ip_addresses'] = ipv4 + ipv4_service + ipv6 + ipv6_service

        if d.get('managed'):
            # Dont default to False
            properties['syslog'] = True

        if d.get('service_tag'):
            properties['service_tag'] = d.get('service_tag')

        helpers.dict_update_node(user, node.handle_id, properties, properties.keys())
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
