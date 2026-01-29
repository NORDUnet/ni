import argparse
import logging
import utils  # noqa: F401 Keep for django_hack

from apps.noclook.models import NodeHandle, NodeType
from norduniclient.exceptions import NodeNotFound
import norduniclient as nc

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

if not logger.handlers:
    ch = logging.StreamHandler()
    logger.addHandler(ch)


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


def delete_host_services(dry_run=True):
    host_type = NodeType.objects.get(slug='host-service')
    host_services = host_type.nodehandle_set.all()

    deleting = '[Dry-run] would delete' if dry_run else 'Deleting'

    logger.warning(f'{deleting} %d host services', len(host_services))
    for host_service in host_services:
        node = host_service.get_node()
        logger.warning(f'{deleting} %d relationships for %s host service', len(
            node.relationships.get('Depends_on', [])), node.data.get('name'))
        if not dry_run:
            host_service.delete()
    if not dry_run:
        host_type.delete()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', action='store_true', default=True)
    args = parser.parse_args()
    delete_host_services(dry_run=not args.commit)


if __name__ == '__main__':
    main()
