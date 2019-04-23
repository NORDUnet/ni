# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from .core import *
from ..models import *

def resolve_roles_list(self, info, **kwargs):
    """
    This method is only present here to illustrate how a manual resolver
    could be used
    """
    neo4jnode = self.get_node()
    relations = neo4jnode.get_outgoing_relations()
    roles = relations.get('Is')

    # this may be the worst way to do it, but it's just for a PoC
    handle_id_list = []
    if roles:
        for role in roles:
            role = role['node']
            role_id = role.data.get('handle_id')
            handle_id_list.append(role_id)

    ret = NodeHandle.objects.filter(handle_id__in=handle_id_list)

    return ret

class RoleType(NIObjectType):
    name = NIStringField(type_kwargs={ 'required': True })

class GroupType(NIObjectType):
    name = NIStringField(type_kwargs={ 'required': True })

class ContactType(NIObjectType):
    name = NIStringField(type_kwargs={ 'required': True })
    first_name = NIStringField(type_kwargs={ 'required': True })
    last_name = NIStringField(type_kwargs={ 'required': True })
    title = NIStringField()
    salutation = NIStringField()
    contact_type = NIStringField()
    phone = NIStringField()
    mobile = NIStringField()
    email = NIStringField()
    other_email = NIStringField()
    PGP_fingerprint = NIStringField()
    is_roles = NIListField(type_args=(RoleType,), manual_resolver=resolve_roles_list)
    member_of_groups = NIListField(type_args=(GroupType,), rel_name='Member_of', rel_method='get_outgoing_relations')
