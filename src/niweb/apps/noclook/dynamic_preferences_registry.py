# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from dynamic_preferences.types import BooleanPreference, StringPreference
from dynamic_preferences import user_preferences_registry, global_preferences_registry


@global_preferences_registry.register
class DataDomain(StringPreference):
    section = 'general'
    name = 'data_domain'
    default = 'nordunet'
    help_text = ''


@global_preferences_registry.register
class PageFlashMessage(StringPreference):
    section = 'announcements'
    name = 'page_flash_message'
    default = ''


@global_preferences_registry.register
class PageFlashMessageLevel(StringPreference):
    section = 'announcements'
    name = 'page_flash_message_level'
    default = 'info'
