# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import logging
from django.db.utils import ProgrammingError
from dynamic_preferences.registries import global_preferences_registry
from .common import *

logger = logging.getLogger('noclook.forms')

try:
    # Load forms for data domain specified in dynamic preferences
    global_preferences = global_preferences_registry.manager()
    domain = global_preferences.get('general__data_domain', '')

    try:
        if domain:
            exec('from .{} import *'.format(domain))
    except ImportError as e:
        logger.error(e)
        logger.error('Customized forms not loaded.')

except ProgrammingError:
    logger.critical('Could not find dynamic preferences table. Have you migrated the db?')
