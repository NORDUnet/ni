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
from django.db import IntegrityError
from apps.noclook.models import NordunetUniqueId

# This script is used for adding the objects collected with the
# NERDS csv producer from the NORDUnet service spreadsheets.

# "host": {
#    "csv_producer": {
#        "comment": "",
#        "customer": "",
#        "depends_on_service": "",
#        "depends_on_supplier": "",
#        "description": "",
#        "end_user_a": "",
#        "end_user_b": "",
#        "equipment_a": "",
#        "equipment_b": "",
#        "meta_type": "",
#        "name": "",
#        "node_type": "",
#        "port_a": "",
#        "port_b": "",
#        "provider": "",
#        "service_component": "",
#        "service_class": "",
#        "service_type": ""
#    },
#    "name": "",
#    "version": 1
# }

def set_customer(node, customer_name):
    """
    Get or creates the customer and depend the customer on the service.
    """
    customer = nt.get_unique_node(customer_name, 'Customer', 'relation')
    rel = nc.create_relationship(nc.neo4jdb, customer, node, 'Uses')
    h.set_noclook_auto_manage(nc.neo4jdb, rel, False)

def set_end_user(node, end_user_name):
    """
    Get or creates the customer and depend the customer on the service.
    """
    end_user = nt.get_unique_node(end_user_name, 'End User', 'relation')
    if not nc.get_relationships(end_user, node, 'Uses'):
        rel = nc.create_relationship(nc.neo4jdb, end_user, node, 'Uses')
        h.set_noclook_auto_manage(nc.neo4jdb, rel, False)

def depend_on_router(node, router_name, port_name):
    """
    Depends the service on a router port.
    Port name is in Juniper notation xxx-X/X/X.
    """
    parent = nt.get_unique_node(router_name, 'Router', 'physical')
    nh = nt.get_node_handle(nc.neo4jdb, port_name, 'Port', 'physical', parent)
    port_node = nh.get_node()
    if not nc.get_relationships(port_node, parent, 'Has'):
        rel = nc.create_relationship(nc.neo4jdb, parent, port_node, 'Has')
        h.set_noclook_auto_manage(nc.neo4jdb, rel, False)
    rel = nc.create_relationship(nc.neo4jdb, node, port_node, 'Depends_on')
    h.set_noclook_auto_manage(nc.neo4jdb, rel, False)

def depend_on_service_component(node, component_name):
    """
    Tries to depend the service on a service component. The criteria is that
    the component already is in the database else the component will be saved as
    a string in the service_component property.
    """
    index = nc.get_node_index(nc.neo4jdb, nc.search_index_name())
    hit = h.iter2list(index['nordunet_id'][component_name])
    if hit:
        rel = nc.create_relationship(nc.neo4jdb, node, hit[0], 'Depends_on')
        h.set_noclook_auto_manage(nc.neo4jdb, rel, False)
    else:
        if node.getProperty('service_component', None):
            with nc.neo4jdb.transaction:
                node['service_component'] = '%s, %s' % (node['service_component'], component_name)
        else:
            with nc.neo4jdb.transaction:
                node['service_component'] = component_name

def depend_on_service(node, service_name, supplier_name):
    """
    Depends the service on another service.
    """
    service = nt.get_unique_node(service_name, 'Service', 'logical')
    if supplier_name:
        with nc.neo4jdb.transaction:
            service['service_class'] = 'External'
            service['service_type'] = 'External'
        supplier = nt.get_unique_node(supplier_name, 'Provider', 'relation')
        if not nc.get_relationships(supplier, service, 'Provides'):
            rel = nc.create_relationship(nc.neo4jdb, supplier, service, 'Provides')
            h.set_noclook_auto_manage(nc.neo4jdb, rel, False)
    rel = nc.create_relationship(nc.neo4jdb, node, service, 'Depends_on')
    h.set_noclook_auto_manage(nc.neo4jdb, rel, False)

def consume_service_csv(json_list, unique_id_set=None):
    """
    Inserts the data collected with NOCLook csv producer.
    """
    for i in json_list:
        node_type = i['host']['csv_producer']['node_type'].title()
        meta_type = i['host']['csv_producer']['meta_type'].lower()
        service_id = i['host']['name']
        if unique_id_set:
            try:
                unique_id_set.objects.create(unique_id=service_id)
            except IntegrityError:
                print "%s already exists in the database. Please check and add manually" % service_id
                continue
        nh = nt.get_unique_node_handle(nc.neo4jdb, service_id, node_type,
                                       meta_type)
        node = nh.get_node()
        h.set_noclook_auto_manage(nc.neo4jdb, node, False)
        with nc.neo4jdb.transaction:
            node['service_class'] = i['host']['csv_producer']['service_class']
            node['service_type'] = i['host']['csv_producer']['service_type']
            description = i['host']['csv_producer'].get('description', None)
            if description:
                node['description'] = description
            node['nordunet_id'] = node['name']
        h.update_node_search_index(nc.neo4jdb, node)
        # Set provider
        provider_name = i['host']['csv_producer'].get('provider')
        provider = nt.get_unique_node(provider_name, 'Provider', 'relation')
        rel = nc.create_relationship(nc.neo4jdb, provider, node, 'Provides')
        h.set_noclook_auto_manage(nc.neo4jdb, rel, False)
        # Depend on router
        equipment_a = i['host']['csv_producer'].get('equipment_a', None)
        if equipment_a:
            depend_on_router(node, equipment_a, i['host']['csv_producer']['port_a'])
        equipment_b = i['host']['csv_producer'].get('equipment_b', None)
        if equipment_b:
            depend_on_router(node, equipment_b, i['host']['csv_producer']['port_b'])
        # Set customer
        customer_name = nt.normalize_whitespace(i['host']['csv_producer']['customer'])
        set_customer(node, customer_name)
        # Set end users
        end_user_a = i['host']['csv_producer'].get('end_user_a', None)
        if end_user_a:
            end_user_a_name = nt.normalize_whitespace(end_user_a)
            set_end_user(node, end_user_a_name)
        end_user_b = i['host']['csv_producer'].get('end_user_b', None)
        if end_user_b:
            end_user_b_name = nt.normalize_whitespace(end_user_b)
            set_end_user(node, end_user_b_name)
        # Depend on service_component
        service_components = i['host']['csv_producer'].get('service_component', None)
        if service_components:
            for component in service_components.split(','):
                component_name = nt.normalize_whitespace(component)
                depend_on_service_component(node, component_name)
        # Depend on services
        depends_on_services = i['host']['csv_producer'].get('depends_on_service', None)
        depends_on_supplier = i['host']['csv_producer'].get('depends_on_supplier', None)
        if depends_on_services and depends_on_supplier:
            for service, supplier in zip(depends_on_services.split(','), depends_on_supplier.split(',')):
                service_name = nt.normalize_whitespace(service)
                supplier_name = nt.normalize_whitespace(supplier)
                depend_on_service(node, service_name, supplier_name)
        elif depends_on_services:
            for service in depends_on_services.split(','):
                service_name = nt.normalize_whitespace(service)
                depend_on_service(node, service_name, None)
        # Set comment
        comment = i['host']['csv_producer'].get('comment', None)
        if comment:
            nt.set_comment(nh, comment)

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
        consume_service_csv(data, NordunetUniqueId)
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
    print 'Total time: %s' % (timedelta)
    return 0

if __name__ == '__main__':
    main()
