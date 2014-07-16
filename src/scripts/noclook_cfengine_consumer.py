#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       noclook_cfengine_consumer.py
#
#       Copyright 2013 Johan Lundberg <lundberg@nordu.net>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import os
import sys
import argparse


## Need to change this path depending on where the Django project is
## located.
#path = '/var/norduni/src/niweb/'
path = '/home/lundberg/norduni/src/niweb/'
##
##
sys.path.append(os.path.abspath(path))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
import norduniclient as nc
from norduni_client_exceptions import MultipleNodesReturned
import noclook_consumer as nt
from apps.noclook import helpers as h

# This script is used for adding the objects collected with the
# cfengine reports NERDS producers to the NOCLook database.

VERBOSE = True

# If the promise exists for the host and is "kept", "not kept" or "repaired" the
# property named "property_name" will be set to the value on the node.
#CFENGINE_MAP = {
#    'promise_name': {
#        'kept': {'property_name': True},
#        'not kept': {'property_name': False},
#        'repaired': {'property_name': 'something else'},
#    }
#}

CFENGINE_MAP = {
    'system_administration_methods_syslog_conf': {
        'kept': {'syslog': True},
        'notkept': {'syslog': False},
        'repaired': {'syslog': True},
    }
}


def insert(json_list):
    """
    Inserts the data loaded from the json files created by
    the nerds producer cfengine_reports.

    "cfengine_report": [
        {
            "last_verified_(gmt_+00:00)": "06-10-2013 16:55",
            "promisehandle": "system_administration_methods_syslog_conf",
            "promisestatus": "kept"
        },
        {
            "last_verified_(gmt_+00:00)": "06-10-2013 16:55",
            "promisehandle": "system_administration_methods_scsi_timeout",
            "promisestatus": "notkept"
        },
    ]
    """
    user = nt.get_user()
    for i in json_list:
        name = i['host']['name']
        promises = i['host']['cfengine_report']
        try:
            node = nc.get_unique_node_by_name(nc.neo4jdb, name, 'Host')
        except MultipleNodesReturned:
            node = None
        if node:
            host_properties = {}
            for promise in promises:
                if promise['promisehandle'] in CFENGINE_MAP.keys():
                    promise_name = promise['promisehandle']
                    promise_status = promise['promisestatus']
                    host_properties.update(CFENGINE_MAP[promise_name][promise_status])

            h.dict_update_node(user, node, host_properties, host_properties.keys())
            if VERBOSE:
                print '%s done.' % name


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', nargs='?', help='Path to the configuration file.')
    args = parser.parse_args()
    # Load the configuration file
    if not args.C:
        print 'Please provide a configuration file with -C.'
        sys.exit(1)
    else:
        config = nt.init_config(args.C)
        cfengine_data = config.get('data', 'cfengine_report')
        if cfengine_data:
            insert(nt.load_json(cfengine_data))
    return 0

if __name__ == '__main__':
    main()
