# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook import helpers
from apps.noclook.forms import *

from .core import NIMutationFactory, CreateNIMutation
from .types import *

class NIRoleMutationFactory(NIMutationFactory):
    create_form    = NewRoleForm
    update_form    = EditRoleForm

    class NIMetaClass:
        node_type      = 'role'
        node_meta_type = 'Logical'
        request_path   = '/'
        form           = NewRoleForm
        nodetype       = RoleType

    class Meta:
        abstract = False

class CreateRoleNIMutation(CreateNIMutation):
    '''This class is not used but left out as documentation in the case that as
    finer grain of control is needed'''
    nodehandle = graphene.Field(RoleType, required=True)

    class NIMetaClass:
        node_type      = 'role'
        node_meta_type = 'Logical'
        request_path   = '/'
        django_form    = NewRoleForm

    class Meta:
        abstract = False

class NOCRootMutation(graphene.ObjectType):
    create_role = NIRoleMutationFactory.get_create_mutation().Field()
    update_role = NIRoleMutationFactory.get_update_mutation().Field()
    delete_role = NIRoleMutationFactory.get_delete_mutation().Field()
