# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

class RoleType(NIObjectType):
    name = NIObjectField(type_kwargs={ 'required': True })

class ContactType(NIObjectType):
    name = NIObjectField(type_kwargs={ 'required': True })
    first_name = NIObjectField(type_kwargs={ 'required': True })
    last_name = NIObjectField(type_kwargs={ 'required': True })
    title = NIObjectField()
    salutation = NIObjectField()
    contact_type = NIObjectField()
    phone = NIObjectField()
    mobile = NIObjectField()
    email = NIObjectField()
    other_email = NIObjectField()
    PGP_fingerprint = NIObjectField()
    is_roles = NIObjectField(field_type=graphene.List, type_args=(RoleType,), rel_name='Is', rel_method='get_outgoing_relations')
