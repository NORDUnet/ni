# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from .core import *
from .types import *
from .query import *
from .mutations import *

NOCSCHEMA_TYPES = [
    RoleType,
    GroupType,
    ContactType,
    NodeHandleType,
]

NOCSCHEMA_QUERIES = [
    NOCRootQuery,
]

NOCSCHEMA_MUTATIONS = [
    NOCRootMutation,
]
