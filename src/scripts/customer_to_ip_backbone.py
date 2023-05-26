import argparse
import logging
import utils

from apps.noclook import helpers
import norduniclient as nc

logger = logging.getLogger('add_customer_to_ip_backbone')


def main(customer_name, dry_run):
    user = utils.get_user()
    customer = utils.get_unique_node_handle(customer_name, 'Customer', 'Relation')
    ip_backbone_services_q = """
    MATCH (s:Service {service_type: 'Backbone'})
    WHERE s.operational_state <> "Decommissioned"
    RETURN s as service
    """
    services = nc.query_to_list(nc.graphdb.manager, ip_backbone_services_q)
    for s in services:
        service = nc.get_node_model(nc.graphdb.manager, node=s['service'])
        if dry_run:
            logger.error('Set %s as customer on IP-Backbone service: %s', customer_name, service.data.get('name'))
            continue
        r, created = helpers.set_user(user, service, customer.handle_id)
        if created:
            logger.error('Set %s as customer on IP-Backbone service: %s', customer_name, service.data.get('name'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', '-n', action='store_true', default=False)
    parser.add_argument('--customer', '-c', required=True)
    args = parser.parse_args()
    logger.setLevel(logging.INFO)

    main(args.customer, args.dry_run)
