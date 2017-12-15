#!/usr/bin/env python

import os
import sys
import argparse
import logging
import utils

# Need to change this path depending on where the Django project is
# located.
base_path = '../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "niweb.settings.prod")

import noclook_consumer as nt
from apps.noclook import helpers
from apps.nerds.lib.consumer_util import address_is_a

logger = logging.getLogger('noclook_consumer.nunoc')
ALLOWED_NODE_TYPE_SET = {'Host'}


def insert_hosts(json_list):
    user = nt.get_user()

    node_type = 'Host'
    meta_type = 'Logical'

    sunet_user = nt.get_unique_node_handle('SUNET', 'Host User', 'Relation')
    for item in json_list:
        name = item['host']['name']
        data = item['host'].get('nunoc_cosmos', {})
        if not address_is_a(data.get('addresses', []), ALLOWED_NODE_TYPE_SET):
            logger.info('%s had an address that belongs to something that is not a host', name)
            continue

        node_handle = nt.get_unique_node_handle_by_name(name, node_type, meta_type, ALLOWED_NODE_TYPE_SET)
        if not node_handle or node_handle.node_type.type not in ALLOWED_NODE_TYPE_SET:
            logger.warning("%s is not in %s", name, ALLOWED_NODE_TYPE_SET)
            continue
        node = node_handle.get_node()
        helpers.update_noclook_auto_manage(node)
        properties = {
            'ip_addresses': data.get('addresses', []),
            'sunet_iaas': data.get('sunet_iaas', False)
        }
        if data.get('managed_by'):
            properties['managed_by'] = data.get('managed_by')
        # Set operational state if it is missing
        if not node.data.get('operational_state', None) and properties['ip_addresses']:
            properties['operational_state'] = 'In service'
        # Update host node
        helpers.dict_update_node(user, node.handle_id, properties)
        if data.get('sunet_iaas', False):
            if node.meta_type == 'Logical':
                helpers.set_user(user, node, sunet_user.handle_id)
            elif node.meta_type == 'Physical':
                helpers.set_owner(user, node, sunet_user.handle_id)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', help='Path to configuration file')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    return parser.parse_args()


def main():
    args = cli()
    if args.verbose:
        logger.setLevel(logging.INFO)
    config = utils.init_config(args.C)
    if config.has_option('data', 'nunoc_cosmos'):
        data_dir = config.get('data', 'nunoc_cosmos')
        insert_hosts(utils.load_json(data_dir))


if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
