# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc

from apps.noclook import helpers
from apps.noclook.forms import *

from .core import NIMutationFactory, CreateNIMutation
from .types import *

class NIGroupMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewGroupForm
        update_form    = EditGroupForm
        request_path   = '/'
        graphql_type   = Group

    class Meta:
        abstract = False

class NIContactMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewContactForm
        update_form    = EditContactForm
        request_path   = '/'
        graphql_type   = Contact

    class Meta:
        abstract = False

class DeleteRole(relay.ClientIDMutation):
    class Input:
        relation_id = graphene.Int(required=True)

    deleted = graphene.Boolean(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        relation_id = input.get("relation_id", None)
        if relation_id:
            role = nc.models.RoleRelationship.get_relationship_model(nc.graphdb.manager, relation_id)
            role.delete()
            return DeleteRole(deleted=True)
        else:
            return DeleteRole(deleted=False)

class NOCRootMutation(graphene.ObjectType):
    create_group   = NIGroupMutationFactory.get_create_mutation().Field()
    update_group   = NIGroupMutationFactory.get_update_mutation().Field()
    delete_group   = NIGroupMutationFactory.get_delete_mutation().Field()

    create_contact = NIContactMutationFactory.get_create_mutation().Field()
    update_contact = NIContactMutationFactory.get_update_mutation().Field()
    delete_contact = NIContactMutationFactory.get_delete_mutation().Field()

    delete_role = DeleteRole.Field()
