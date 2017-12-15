# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
import utils

__author__ = 'lundberg'

## Need to change this path depending on where the Django project is
## located.
base_path = '../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "niweb.settings.prod")

import noclook_consumer as nt
from apps.noclook import helpers

logger = logging.getLogger('noclook_consumer.csv')

#
# Inserts objects from NERDS csv_producer data
#


def insert_site(site_dict):
    """
    :param site_dict: data
    :type site_dict: dict
    :return: None
    :rtype: None

    Expected dict
    {
        u'name': u'',
        u'area': u'',
        u'country': u'',
        u'longitude': u'',
        u'node_type': u'Site',
        u'meta_type': u'Location',
        u'site_owner': u'',
        u'latitude': u'',
        u'site_type': u''
    }
    """

    user = nt.get_user()
    # Remove meta data and relationship data from the site dict
    name = site_dict.pop('name')
    node_type = site_dict.pop('node_type')
    meta_type = site_dict.pop('meta_type')
    site_owner = site_dict.pop('site_owner')
    # Get or create Site
    site_nh = nt.get_unique_node_handle(name, node_type, meta_type)
    # Set or update node properties
    helpers.dict_update_node(user, site_nh.handle_id, site_dict, site_dict.keys())
    if site_owner:
        # Get or create Site owner
        site_owner_nh = nt.get_unique_node_handle(site_owner, 'Site Owner', 'Relation')
        # Set relationship to site owner
        helpers.set_responsible_for(user, site_nh.get_node(), site_owner_nh.handle_id)
    logger.info(u'Imported site {}.'.format(name))


def run_consume(path):
    data = utils.load_json(path)
    for item in data:
        node_type = item['host']['csv_producer']['node_type']
        if node_type == 'Site':
            insert_site(item['host']['csv_producer'])
        else:
            logger.warning('Node type {} not known.' % node_type)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', nargs='?', help='Path to the data directory.')
    parser.add_argument('-V', action='store_true', default=False)
    args = parser.parse_args()
    # Load the configuration file
    if not args.D:
        print 'Please provide a path to the data directory with -D.'
        sys.exit(1)
    if args.V:
        logger.setLevel(logging.INFO)

    print 'Inserting data...'
    run_consume(args.D)
    print 'done.'
    return 0

if __name__ == '__main__':
    main()
