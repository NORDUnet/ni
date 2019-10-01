# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from djangovakt.storage import DjangoStorage
from vakt import Guard, RulesChecker


def get_vakt_storage_and_guard():
    storage = DjangoStorage()
    guard = Guard(storage, RulesChecker())

    return storage, guard
