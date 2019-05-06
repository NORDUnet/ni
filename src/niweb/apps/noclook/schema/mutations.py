# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook import helpers
from apps.noclook.forms import *

from .core import NIMutationFactory, CreateNIMutation
from .types import *

class NIRoleMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewRoleForm
        update_form    = EditRoleForm
        request_path   = '/'
        graphql_type   = RoleType

    class Meta:
        abstract = False

class NIGroupMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewGroupForm
        update_form    = EditGroupForm
        request_path   = '/'
        graphql_type   = GroupType

    class Meta:
        abstract = False

class NIContactMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewContactForm
        update_form    = EditContactForm
        request_path   = '/'
        graphql_type   = ContactType

    class Meta:
        abstract = False

class CreateRoleNIMutation(CreateNIMutation):
    '''This class is not used but left out as documentation in the case that as
    finer grain of control is needed'''
    nodehandle = graphene.Field(RoleType, required=True)

    class NIMetaClass:
        request_path   = '/'
        django_form    = NewRoleForm
        graphql_type   = RoleType

    class Meta:
        abstract = False

class NOCRootMutation(graphene.ObjectType):
    create_role    = NIRoleMutationFactory.get_create_mutation().Field()
    update_role    = NIRoleMutationFactory.get_update_mutation().Field()
    delete_role    = NIRoleMutationFactory.get_delete_mutation().Field()

    create_group   = NIGroupMutationFactory.get_create_mutation().Field()
    update_group   = NIGroupMutationFactory.get_update_mutation().Field()
    delete_group   = NIGroupMutationFactory.get_delete_mutation().Field()

    create_contact = NIContactMutationFactory.get_create_mutation().Field()
    update_contact = NIContactMutationFactory.get_update_mutation().Field()
    delete_contact = NIContactMutationFactory.get_delete_mutation().Field()
