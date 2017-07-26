# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from dynamic_preferences.types import StringPreference, Section
from dynamic_preferences.registries import global_preferences_registry
from models import UniqueIdGenerator

general = Section('general')
announcements = Section('announcements')
id_gen = Section('id_generators')


@global_preferences_registry.register
class DataDomain(StringPreference):
    section = general
    name = 'data_domain'
    default = 'common'
    help_text = 'Used for dynamic loading of forms (restart required)'


@global_preferences_registry.register
class MoreInfoLink(StringPreference):
    section = general
    name = 'more_info_link'
    default = 'https://portal.nordu.net/display/nordunetops/'
    help_text = 'Base url for more information links on detail pages'


@global_preferences_registry.register
class PageFlashMessage(StringPreference):
    section = announcements
    name = 'page_flash_message'
    default = ''
    help_text = 'Announcement message'


@global_preferences_registry.register
class PageFlashMessageLevel(StringPreference):
    section = announcements
    name = 'page_flash_message_level'
    default = 'info'
    help_text = 'info|warning|danger'


@global_preferences_registry.register
class ServiceIdGenerator(StringPreference):
    section = id_gen
    name = 'services'
    default = ''
    help_text = 'Which id generator to use for services'
    model = UniqueIdGenerator
