#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse
from configparser import SafeConfigParser
import utils
from apps.noclook import helpers

logger = logging.getLogger('noclook_consumer.checkmk')

# This consumer is used for adding raritan PDUs to noclook.

"""
{
    "host": {
        "version": 1,
        "name": "test",
        "raritan": {
            "ports": [
                {
                    "name": "4",
                    "description": "someserver.nordu.net"
                },
                {
                    "name": "9",
                    "description": "server04"
                },
                {
                    "name": "10",
                    "description": "test06"
                },
                {
                    "name": "11",
                    "description": "another.nordu.net"
                },
                {
                    "name": "12",
                    "description": "stardust.nordu.net"
                }
            ]
        }
    }
}
"""


def insert(json_list):
    for item in json_list:
        base = item['host'].get('raritan')
        pdu_handle = utils.get_unique_node_handle_by_name(item['host']['name'], 'PDU', 'Physical', ['Host', 'PDU'])
        pdu_node = pdu_handle.get_node()
        helpers.update_noclook_auto_manage(pdu_node)
        # If needed add node update with ip/hostnames

        insert_ports(base.get('ports'), pdu_node)


def insert_ports(ports, pdu_node):
    user = utils.get_user()
    for port in ports:
        port_name = port.get('name')
        if port_name:
            port_node = get_or_create_port(port_name, pdu_node, user)
            helpers.set_noclook_auto_manage(port_node, True)
            property_keys = ['description', 'name']
            helpers.dict_update_node(user, port_node.handle_id, port, property_keys)


def get_or_create_port(port_name, node, user):
    result = node.get_port(port_name)
    if 'Has' in result:
        port_node = result.get('Has')[0].get('node')
    else:
        port_handle = utils.create_node_handle(port_name, 'Port', 'Physical')
        port_node = port_handle.get_node()
        helpers.set_has(user, node, port_node.handle_id)
    return port_node


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file')
    parser.add_argument('--verbose', '-V', default=False, action='store_true', help='Verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)
    config = SafeConfigParser()
    config.read(args.C)

    if config.has_option('data', 'raritan'):
        data_dir = config.get('data', 'raritan')
        insert(utils.load_json(data_dir))


if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
