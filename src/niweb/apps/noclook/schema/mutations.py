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

class NIProcedureMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewProcedureForm
        update_form    = EditProcedureForm
        request_path   = '/'
        graphql_type   = Procedure

    class Meta:
        abstract = False

def process_works_for(request, form, nodehandler, relation_name):
    organization_nh = NodeHandle.objects.get(pk=form.cleaned_data[relation_name])
    role_name = form.cleaned_data['role_name']
    helpers.set_works_for(request.user, nodehandler, organization_nh.handle_id, role_name)

def process_member_of(request, form, nodehandler, relation_name):
    group_nh = NodeHandle.objects.get(pk=form.cleaned_data[relation_name])
    helpers.set_member_of(request.user, nodehandler, group_nh.handle_id)

class NIContactMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewContactForm
        update_form    = EditContactForm
        request_path   = '/'
        graphql_type   = Contact
        relations_processors = {
            'relationship_works_for': process_works_for,
            'relationship_member_of': process_member_of,
        }

    class Meta:
        abstract = False

class NIOrganizationMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewOrganizationForm
        update_form    = EditOrganizationForm
        request_path   = '/'
        graphql_type   = Organization
        # create_include or create_exclude
        # update_include or update_exclude
        update_exclude = ('abuse_contact', 'primary_contact',
                            'secondary_contact', 'it_technical_contact',
                            'it_security_contact', 'it_manager_contact')

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
    create_group        = NIGroupMutationFactory.get_create_mutation().Field()
    update_group        = NIGroupMutationFactory.get_update_mutation().Field()
    delete_group        = NIGroupMutationFactory.get_delete_mutation().Field()

    create_procedure    = NIProcedureMutationFactory.get_create_mutation().Field()
    update_procedure    = NIProcedureMutationFactory.get_update_mutation().Field()
    delete_procedure    = NIProcedureMutationFactory.get_delete_mutation().Field()

    create_contact      = NIContactMutationFactory.get_create_mutation().Field()
    update_contact      = NIContactMutationFactory.get_update_mutation().Field()
    delete_contact      = NIContactMutationFactory.get_delete_mutation().Field()

    create_organization = NIOrganizationMutationFactory.get_create_mutation().Field()
    update_organization = NIOrganizationMutationFactory.get_update_mutation().Field()
    delete_organization = NIOrganizationMutationFactory.get_delete_mutation().Field()

    delete_relationship = DeleteRelationship.Field()
