import argparse
import logging
from datetime import date, timedelta
import utils  # noqa: F401 Keep for django_hack

from apps.noclook.models import NodeHandle, NodeType
from apps.noclook import helpers
import norduniclient as nc

from actstream.models import Action

logger = logging.getLogger('noclook_cleanup_peering_partners')


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    parser.add_argument('--dry-run', '-N', action='store_true', default=False)

    parser.add_argument('--max-age', '-t', type=int, default=365, help='Number of days to use as cut off')
    parser.add_argument('--purge', '-p', action='store_true', default=False, help='Purge mode will also delete the node handle for the host service')

    return parser.parse_args()


def count_dependencies(handle_id, last_seen):
    q_deps = """
    MATCH (n:Host_Service  {handle_id: $handle_id})-[r:Depends_on]->(n2:Node)
    WHERE r.noclook_last_seen < $last_seen
    RETURN count(r) as count
    """
    result = nc.query_to_dict(
        nc.graphdb.manager,
        q_deps,
        handle_id=handle_id,
        last_seen=last_seen,
    )
    return result['count']


def cleanup_host_service(nh, max_last_seen, dry_run):
    logger.info('Cleaning old dependencies and activity log for %s', nh.node_name)
    dep_count = count_dependencies(nh.handle_id, max_last_seen.isoformat())
    if dry_run:
        logger.warning("[Dry-run] would delete %d old dependencies for %s (%s)", dep_count, nh.node_name, nh.handle_id)
    else:
        q_delete_deps = """
        MATCH (n:Host_Service  {handle_id: $handle_id})-[r:Depends_on]->(n2:Node)
        WHERE r.noclook_last_seen < $last_seen
        DELETE r
        """
        # remove old relations
        nc.query_to_dict(
            nc.graphdb.manager,
            q_delete_deps,
            handle_id=nh.handle_id,
            last_seen=max_last_seen.isoformat(),
        )
        logger.warning("Deleted %d old dependencies for %s (%s)", dep_count, nh.node_name, nh.handle_id)
        # clean up activity log
        # Just delete old stuffA as it is useless
        # Not year 10000 proof :P
        actions = Action.objects.filter(
            action_object_object_id=nh.handle_id,
            timestamp__lt=max_last_seen
        )
        if dry_run:
            logger.warning("[Dry-run] would delete %s activity log entries for %s (%s)", actions.count(), nh.node_name, nh.handle_id)
        else:
            action_count, _ = actions.delete()
            logger.warning("Deleted %s activity log entries for %s (%s)", action_count, nh.node_name, nh.handle_id)


def cleanup_host_services(max_age, purge, dry_run):
    max_age_hours = max_age * 24
    max_last_seen = date.today() - timedelta(days=max_age)
    host_service_type = NodeType.objects.get(type='Host Service')

    host_services = NodeHandle.objects.filter(node_type=host_service_type)

    for nh in host_services:
        node = nh.get_node()
        last_seen, expired = helpers.neo4j_data_age(node.data, max_age_hours)
        if purge:
            if expired:
                logger.warning('Deleting Host Service "%s"', nh.node_name)
                if not dry_run:
                    nh.delete()
            else:
                # Cleanup old stuff
                cleanup_host_service(nh, max_last_seen, dry_run)
        else:
            cleanup_host_service(nh, max_last_seen, dry_run)


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
