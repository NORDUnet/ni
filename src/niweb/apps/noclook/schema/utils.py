# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from dynamic_preferences.registries import global_preferences_registry
from django.db.utils import ProgrammingError

def sunet_forms_enabled():
    try:
        global_preferences = global_preferences_registry.manager()
        domain = global_preferences.get('general__data_domain', '')

        if domain and domain == 'sunet':
            return True
    except ProgrammingError:
        pass

    return False
