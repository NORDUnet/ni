import argparse
import logging
import utils  # noqa: F401 Keep for django_hack

from apps.noclook.models import NodeHandle, NodeType
from apps.noclook import helpers

logger = logging.getLogger('noclook_cleanup_peering_partners')


NEVER_DELETE = {
    'git',
    'http',
    'https',
    'snmp',
    'bgp',
    'ldap',
    'ldaps',
    'ntp',
    'nrpe',  # or what?
    'ftp',
}


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    parser.add_argument('--dry-run', '-N', action='store_true', default=False)

    parser.add_argument('--max-age', '-t', type=int, default=365, help='Number of days to use as cut off')
    parser.add_argument('--purge', '-p', action='store_true', default=False, help='Purge mode will also delete the node handle for the host service')

    return parser.parse_args()


def cleanup_host_services(max_age, purge, dry_run):
    max_age_hours = max_age * 24
    host_service_type = NodeType.objects.get(type='Host Service')

    host_services = NodeHandle.objects.filter(node_type=host_service_type)

    for nh in host_services:
        node = nh.get_node()
        last_seen, expired = helpers.neo4j_data_age(node.data, max_data_age=max_age_hours)
        if expired:
            if purge:
                logger.warning('Deleting Host Service "%s"', nh.node_name)
                if not dry_run:
                    nh.delete()
            else:
                logger.warning('Cleaning old relations and activity log for %s', nh.node_name)


def main():
    args = cli()

    if args.verbose:
        logger.setLevel(logging.INFO)

    cleanup_host_services(args.max_age, args.purge, args.dry_run)


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
