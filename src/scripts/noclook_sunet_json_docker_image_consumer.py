# -*- coding: utf-8 -*-

import sys
import argparse
import logging
import utils

__author__ = 'markus'


from apps.noclook import helpers
logger = logging.getLogger('noclook_consumer.sunet_docker_image_json')

#
# Inserts objects from SUNET docker image json
#


def insert_docker_image(img_name, img_data):
    user = utils.get_user()
    name = img_name
    node_type = 'Docker Image'
    default_meta_type = 'Logical'

    # Get or create host
    docker_image_nh = utils.get_unique_node_handle(name, node_type, default_meta_type)

    docker_data = {
        'packages': [f"{p['package']} {p['version']}" for p in img_data['pkg_list']],
    }

    if img_data.get('os_hash', {}).get('PRETTY_NAME'):
        docker_data['os'] = img_data['os_hash']['PRETTY_NAME']

    if isinstance(img_data['inspect_data'], list) and len(img_data['inspect_data']) > 0 and isinstance(img_data['inspect_data'][0], list):
        # XXX: workaround for current format
        inspect_data = img_data['inspect_data'][0]
    if 'Created' in inspect_data:
        # the neo4j date format we are using is '%Y-%m-%dT%H:%M:%S.%f' per noclook_last_seen_to_dt
        non_nano, rest = inspect_data['Created'].split('.')
        docker_data['image_created'] = f'{non_nano}.{rest[:6]}'

    if 'RepoTags' in inspect_data:
        docker_data['tags'] = inspect_data['RepoTags']

    # Set or update node properties
    helpers.dict_update_node(user, docker_image_nh.handle_id, docker_data, docker_data.keys())
    logger.info(u'Imported site {}.'.format(name))


def run_consume(path):
    data = utils.load_json(path)
    for item in data:
        first_val = list(item.values())[0]
        if 'pkg_list' in first_val and 'inspect_data' in first_val:
            for img_name, img_data in item.items():
                insert_docker_image(img_name, img_data)
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
    if not len(logger.handlers):
        logger.propagate = False
        logger.setLevel(logging.WARNING)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    main()
