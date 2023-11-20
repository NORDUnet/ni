# -*- coding: utf-8 -*-

import sys
import argparse
import logging
import utils

__author__ = 'markus'


from apps.noclook import helpers
logger = logging.getLogger('noclook_consumer.sunet_host_json')

#
# Inserts objects from NERDS csv_producer data
#


def insert_node(node_dict):
    """
    :param node_dict:
    :type node_dict: dict
    :return: None
    :rtype: None

    Expected dict
    {
        u'name': u'',
        u'values': {},
    }
    """

    user = utils.get_user()
    values = node_dict.get('values', {}) or {}
    networking = values.get('networking', {}) or {}
    if not networking:
        logger.error('values.networking is empty')
        return
    name = networking.get('fqdn')
    node_type = 'Host'
    default_meta_type = 'Logical'

    # Get or create host
    host_nh = utils.get_unique_node_handle(name, node_type, default_meta_type)
    host = host_nh.get_node()

    ip_addresses = []
    if networking.get('ip'):
        ip_addresses.append(networking.get('ip'))
    if networking.get('ip6'):
        ip_addresses.append(networking.get('ip6'))

    host_data = {
        'ip_addresses': ip_addresses,
    }

    if values.get('os', {}).get('description'):
        host_data['os'] = values['os']['description']
    elif values.get('lsbdistdescription'):
        host_data['os'] = values['lsbdistdescription']

    if values.get('cosmos_repo'):
        # assume the host is managed by cosmos (which means puppet)
        host_data['managed_by'] = 'Puppet'
        if values.get('cosmos_repo_origin_url'):
            host_data['cosmos_repo_origin_url'] = values.get('cosmos_repo_origin_url')

    else:
        host_data['managed_by'] = 'Manual'

    packages = values.get('packages', [])
    if packages:
        # find docker-ce
        docker_ce = [p['version'] for p in packages if isinstance(p, dict) and p.get('name') == 'docker-ce']
        if docker_ce:
            host_data['docker_version'] = docker_ce[0]

    if values.get('docker_ps'):
        # old way was just a list on host, now we have docker-images nodes
        host_data['docker_images'] = [c['Image'] for c in values.get('docker_ps') if 'Image' in c]
        # associate docker image and host
        existing_docker_images = {}
        for dep in host.get_dependencies().get('Depends_on', {}):
            # check if relation involves a Docker_Image
            if any(['Docker_Image' in n.labels for n in dep['relationship'].nodes]):
                existing_docker_images[dep['node'].data['name']] = dep['relationship_id']

        new_docker_images = set()
        for container in values.get('docker_ps'):
            if 'Image' in container:
                # consider caching docker image nodes?
                docker_image_nh = get_or_insert_docker_image(container)
                new_docker_images.add(docker_image_nh.node_name)
                helpers.set_depends_on(user, host, docker_image_nh.handle_id)
        # cleanup old docker images
        to_clean_docker = set(existing_docker_images.keys()) - new_docker_images
        for img in to_clean_docker:
            helpers.delete_relationship(user, existing_docker_images[img])

    # Set or update node properties
    helpers.dict_update_node(user, host_nh.handle_id, host_data, host_data.keys())
    logger.info(u'Imported site {}.'.format(name))


def get_or_insert_docker_image(node_dict):
    name = node_dict['Image']
    node_type = 'Docker Image'
    node_meta_type = 'Logical'
    return utils.get_unique_node_handle(name, node_type, node_meta_type)


def run_consume(path):
    data = utils.load_json(path)
    for item in data:
        if 'name' in item and 'values' in item:
            # got a node1 json formatted
            insert_node(item)
        else:
            logger.warning('Unknown json format not supported.')


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', nargs='?', help='Path to the data directory.')
    parser.add_argument('-V', action='store_true', default=False)
    args = parser.parse_args()
    # Load the configuration file
    if not args.D:
        print('Please provide a path to the data directory with -D.')
        sys.exit(1)
    if args.V:
        logger.setLevel(logging.INFO)

    print('Inserting data...')
    run_consume(args.D)
    print('done.')
    return 0


if __name__ == '__main__':
    main()
