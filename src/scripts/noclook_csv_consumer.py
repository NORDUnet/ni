import utils
import argparse
import csv
import logging
from apps.noclook import helpers

logger = logging.getLogger('noclook_csv_consumer')


def create_new_ports(parent_node, ports, user):
    existing_ports = [item.get('node').data.get('name') for item in parent_node.get_ports().get('Has') if item.get('node')]
    for port_name in [port for port in ports if port not in existing_ports]:
        helpers.create_port(parent_node, port_name, user)


def insert_physical_host(data):
    """
    Dict expected to have keys:
        name
    Optional:
        located_in, rack_units, rack_position, ports, responsible_group, support_group
    """
    user = utils.get_user()
    node_type = 'Host'
    meta_type = 'Physical'
    node_handle = utils.get_unique_node_handle(data['name'], node_type, meta_type)

    node = node_handle.get_node()
    properties = {
        'rack_units': int(data.get('rack_units', 1)),
        'rack_position': int(data.get('rack_position', -1)),
        'responsible_group': data.get('responsible_group', 'SEI'),
        'support_group': data.get('support_group', 'SEI'),
    }

    helpers.dict_update_node(user, node_handle.handle_id, properties)

    # handle ports

    ports = [port.strip() for port in data.get('ports', '').split(';')]
    create_new_ports(node, ports, user)
    logger.info('Done with %s', node.data['name'])

    # Set location
    if data.get('located_in'):
        helpers.set_location(user, node, int(data['located_in']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file', help='The csv file to import')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    with open(args.csv_file) as csv_file:
        rows = csv.DictReader(csv_file)
        for row in rows:
            if row['type'] == 'PhysicalHost':
                insert_physical_host(row)
            else:
                logger.error('The type %s is currently not supported. row: %s', row['type'], row)


if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
