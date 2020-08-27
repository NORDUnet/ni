# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from dynamic_preferences.registries import global_preferences_registry


def sunet_forms_enabled():
    global_preferences = global_preferences_registry.manager()
    domain = global_preferences.get('general__data_domain', '')

    if domain and domain == 'sunet':
        return True

    return False
