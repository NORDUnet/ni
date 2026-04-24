# -*- coding: utf-8 -*-
#
#       delete_handle_ids.py
#

import argparse
import csv
import logging
import utils

from django.core.exceptions import ObjectDoesNotExist
from apps.noclook import helpers
from apps.noclook.models import NodeHandle

logger = logging.getLogger('noclook_delete_handle_ids')


delete_log = []
user = utils.get_user()


def delete_handle_id(handle_id, dry_run):
    try:
        nh = NodeHandle.objects.get(pk=handle_id)
        name = f"{nh.node_type.type}<name='{nh.node_name}', handle_id={nh.handle_id}>"
    except ObjectDoesNotExist:
        return

    if not dry_run:
        helpers.delete_node(user, handle_id)
    logger.info('Deleted node {}.'.format(name))
    delete_log.append(name)


def main():
    # User friendly usage output
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file', help='CSV file with a header row, where handel_id is a column')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    parser.add_argument('--dry-run', '-N', action='store_true', default=False)
    args = parser.parse_args()
    # Load the configuration file
    if args.verbose:
        logger.setLevel(logging.INFO)

    with open(args.csv_file, "r", encoding='utf-8-sig') as csv_file:
        rows = csv.DictReader(csv_file)
        for row in rows:
            delete_handle_id(row['handle_id'], args.dry_run)

    if delete_log:
        logger.warning("Deleted %s nodes", len(delete_log))
    return 0


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
