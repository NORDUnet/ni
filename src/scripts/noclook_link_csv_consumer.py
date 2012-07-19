# -*- coding: utf-8 -*-
"""
Created on 2012-07-04 12:12 PM

@author: lundberg
"""

import sys
import os
import datetime
import argparse

## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
import noclook_consumer as nt
import norduni_client as nc
from apps.noclook import helpers as h

# This script is used for adding the objects collected with the
# NERDS csv producer from the NORDUnet service spreadsheets.

# "host": {
#     "csv_producer": {
#         "equipment_a": "",
#         "equipment_b": "",
#         "link_type": "",
#         "meta_type": "",
#         "name": "",
#         "node_type": "",
#         "patches": "",
#         "port_a": "",
#         "port_b": "",
#         "rack_a": "",
#         "rack_b": "",
#         "slot_a": "",
#         "slot_b": "",
#         "subrack_a": "",
#         "subrack_b": ""
#     },
#     "name": "",
#     "version": 1
# }

def depend_on_equipment(node, equipment, rack, subrack, slot, port):
    """
    Depends the link on supplied equipment and port.
    Port name is in Alcatel-Lucent notation rXsrXslX/port#X.
    """
    parent = nt.get_unique_node(equipment, 'Optical Node', 'physical')
    port_name = 'r%dsr%dsl%d/port#%d' % (int(rack), int(subrack),
                                         int(slot), int(port))
    nh = nt.get_node_handle(nc.neo4jdb, port_name, 'Port', 'physical', parent)
    port_node = nh.get_node()
    h.set_noclook_auto_manage(nc.neo4jdb, port_node, False)
    rel = nc.create_relationship(nc.neo4jdb, parent, port_node, 'Has')
    h.set_noclook_auto_manage(nc.neo4jdb, rel, False)
    rel = nc.create_relationship(nc.neo4jdb, node, port_node, 'Depends_on')
    h.set_noclook_auto_manage(nc.neo4jdb, rel, False)


def consume_link_csv(json_list):
    """
    Inserts the data collected with NOCLook csv producer.
    """
    for i in json_list:
        node_type = i['host']['csv_producer']['node_type'].title()
        meta_type = i['host']['csv_producer']['meta_type'].lower()
        nh = nt.get_unique_node_handle(nc.neo4jdb, i['host']['name'], node_type,
                                       meta_type)
        node = nh.get_node()
        h.set_noclook_auto_manage(nc.neo4jdb, node, False)
        with nc.neo4jdb.transaction:
            node['link_type'] = i['host']['csv_producer']['link_type']
            patches = i['host']['csv_producer'].get('patches', None)
            if patches:
                node['patches'] = patches
            node['nordunet_id'] = node['name']
        h.update_node_search_index(nc.neo4jdb, node)
        # TODO: Insert id in to NORDUnetIDSet table.
        # Depend on equipment
        equipment_a = i['host']['csv_producer'].get('equipment_a', None)
        if equipment_a:
            depend_on_equipment(node, equipment_a,
                                i['host']['csv_producer']['rack_a'],
                                i['host']['csv_producer']['subrack_a'],
                                i['host']['csv_producer']['slot_a'],
                                i['host']['csv_producer']['port_a'])
        equipment_b = i['host']['csv_producer'].get('equipment_b', None)
        if equipment_b:
            depend_on_equipment(node, equipment_b,
                                i['host']['csv_producer']['rack_b'],
                                i['host']['csv_producer']['subrack_b'],
                                i['host']['csv_producer']['slot_b'],
                                i['host']['csv_producer']['port_b'])

def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', nargs='?',
                        help='Path to the json data.')

    args = parser.parse_args()
    # Start time
    start = datetime.datetime.now()
    timestamp_start = datetime.datetime.strftime(start,
                                                 '%b %d %H:%M:%S')
    print '%s noclook_consumer.py was started.' % timestamp_start
    # Insert data from known data sources if option -I was used
    if args.D:
        print 'Loading data...'
        data = nt.load_json(args.D)
        print 'Inserting data...'
        consume_link_csv(data)
        print 'noclook consume done.'
    else:
        print 'Use -D to provide the path to the JSON files.'
        sys.exit(1)
        # end time
    end = datetime.datetime.now()
    timestamp_end = datetime.datetime.strftime(end,
                                               '%b %d %H:%M:%S')
    print '%s noclook_consumer.py ran successfully.' % timestamp_end
    timedelta = end - start
    print 'Total time: %s' % timedelta
    return 0

if __name__ == '__main__':
    main()
