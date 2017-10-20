import os
from os.path import join
import logging
import json

logger = logging.getLogger('noclook_utils')


def load_json(json_dir, starts_with=''):
    """
    Thinks all files in the supplied dir are text files containing json.
    """
    logger.info('Loading data from {!s}.'.format(json_dir))
    try:
        for subdir, dirs, files in os.walk(json_dir):
            gen = (_file for _file in files if _file.startswith(starts_with))
            for a_file in gen:
                try:
                    f = open(join(json_dir, a_file), 'r')
                    yield json.load(f)
                except ValueError as e:
                    logger.error('Encountered a problem with {f}.'.format(f=a_file))
                    logger.error(e)
    except IOError as e:
        logger.error('Encountered a problem with {d}.'.format(d=json_dir))
        logger.error(e)
