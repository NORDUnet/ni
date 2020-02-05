import argparse
import logging
import utils  # noqa: F401 Keep for django_hack
from apps.noclook.models import NodeType, NodeHandle
from actstream.models import Action

logger = logging.getLogger('noclook_cleanup_peering_partners')


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    parser.add_argument('--dry-run', '-N', action='store_true', default=False)
    return parser.parse_args()


def cleanup_activity_created(node_handles, dry_run=False):
    total_deleted = 0
    for nh in node_handles:
        node_log = {}
        to_delete = set()
        for action in nh.action_object_actions.all().reverse():
            # could also check if action.data.noclook.action_type == relationship
            previous_action = node_log.get(action.target_object_id)
            if previous_action == action.verb:
                if action.verb == 'create':
                    logger.info('Mark for deletion %s for %s', action, nh)
                    to_delete.add(action.id)
            else:
                node_log[action.target_object_id] = action.verb
        deletions = len(to_delete)
        if deletions > 0:
            if not dry_run:
                Action.objects.filter(id__in=to_delete).delete()
            total_deleted += deletions
            logger.warning('Deleted %d useless actions for %s (%s)', deletions, nh, nh.handle_id)
    logger.warning('Total usless actions deleted: %d', total_deleted)


def cleanup_missing_description(dry_run=False):
    count = 0
    for nh in NodeHandle.objects.filter(node_type__type='Peering Partner', node_name='Missing description'):
        node = nh.get_node()
        if node.data.get('as_number') == '0':
            if not dry_run:
                nh.delete()
            count += 1
    logger.warning('Total missing description peering partners deleted: %d', count)


def main():
    args = cli()

    # Load the configuration file
    if args.verbose:
        logger.setLevel(logging.INFO)

    # get all peering partners
    peer_type = NodeType.objects.get(type='Peering Partner')
    nh_peers = NodeHandle.objects.filter(node_type=peer_type)

    cleanup_activity_created(nh_peers, args.dry_run)
    cleanup_missing_description(args.dry_run)


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
