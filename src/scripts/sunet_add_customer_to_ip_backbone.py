import argparse
import logging
import utils

from apps.noclook import helpers
import norduniclient as nc

logger = logging.getLogger('sunet_add_customer_to_ip_backbone')


def main(dry_run):
    user = utils.get_user()
    sunet = utils.get_unique_node_handle('SUNET', 'Customer', 'Relation')
    ip_backbone_services_q = """
    MATCH (s:Service {service_type: 'Backbone'})
    WHERE s.operational_state <> "Decommissioned"
    RETURN s as service
    """
    services = nc.query_to_list(nc.graphdb.manager, ip_backbone_services_q)
    for s in services:
        service = nc.get_node_model(nc.graphdb.manager, node=s['service'])
        if dry_run:
            logger.info('Set SUNET as customer on IP-Backbone service: %s', service.data.get('name'))
            continue
        r, created = helpers.set_user(user, service, sunet.handle_id)
        if created:
            logger.info('Set SUNET as customer on IP-Backbone service: %s', service.data.get('name'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', '-n', action='store_true', default=False)
    args = parser.parse_args()
    logger.setLevel(logging.INFO)

    main(args.dry_run)
