# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc

from apps.noclook import activitylog, helpers
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

class DeleteRelationship(relay.ClientIDMutation):
    class Input:
        relation_id = graphene.Int(required=True)

    success = graphene.Boolean(required=True)
    relation_id = graphene.Int(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        relation_id = input.get("relation_id", None)
        success = False

        try:
            relationship = nc.get_relationship_model(nc.graphdb.manager, relation_id)
            activitylog.delete_relationship(info.context.user, relationship)
            relationship.delete()
            success = True
        except nc.exceptions.RelationshipNotFound:
            success = True

        return DeleteRelationship(success=success, relation_id=relation_id)

class NOCRootMutation(graphene.ObjectType):
    create_group   = NIGroupMutationFactory.get_create_mutation().Field()
    update_group   = NIGroupMutationFactory.get_update_mutation().Field()
    delete_group   = NIGroupMutationFactory.get_delete_mutation().Field()

    create_contact = NIContactMutationFactory.get_create_mutation().Field()
    update_contact = NIContactMutationFactory.get_update_mutation().Field()
    delete_contact = NIContactMutationFactory.get_delete_mutation().Field()

    delete_relationship = DeleteRelationship.Field()
