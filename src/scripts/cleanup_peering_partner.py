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


def main():
    args = cli()

    # Load the configuration file
    if args.verbose:
        logger.setLevel(logging.INFO)

    # get all peering partners
    peer_type = NodeType.objects.get(type='Peering Partner')
    nh_peers = NodeHandle.objects.filter(node_type=peer_type)
    # for each check activity log
    total_deleted = 0
    for peer_nh in nh_peers:
        peer_log = {}
        to_delete = set()
        for action in peer_nh.action_object_actions.all().reverse():
            # could also check if action.data.noclook.action_type == relationship
            previous_action = peer_log.get(action.target_object_id)
            if previous_action == action.verb:
                if action.verb == 'create':
                    logger.info('Mark for deletion %s for %s', action, peer_nh)
                    to_delete.add(action.id)
            else:
                peer_log[action.target_object_id] = action.verb
        deletions = len(to_delete)
        if deletions > 0:
            if not args.dry_run:
                Action.objects.filter(id__in=to_delete).delete()
            total_deleted += deletions
            logger.warning('Deleted %d useless actions for %s (%s)', deletions, peer_nh, peer_nh.handle_id)
    logger.warning('Total usless actions deleted: %d', total_deleted)


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
