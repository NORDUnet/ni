# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc

from apps.noclook import activitylog, helpers
from apps.noclook.forms import *
from apps.noclook.models import Dropdown as DropdownModel

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

def process_abuse_contact(request, form, nodehandler, relation_name):
    group_nh = NodeHandle.objects.get(pk=form.cleaned_data[relation_name])
    helpers.set_member_of(request.user, nodehandler, group_nh.handle_id)

class NIOrganizationMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewOrganizationForm
        update_form    = EditOrganizationForm
        request_path   = '/'
        graphql_type   = Organization
        # create_include or create_exclude

    class Meta:
        abstract = False

class UpdateNIOrganizationMutation(UpdateNIMutation):
    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()
        handle_id      = request.POST.get('handle_id')

        # Get needed data from node
        nh, organization = helpers.get_nh_node(handle_id)
        relations = organization.get_relations()
        out_relations = organization.get_outgoing_relations()
        if request.POST:
            form = form_class(request.POST.copy())
            if form.is_valid():
                # Generic node update
                # use property keys to avoid inserting contacts as a string property of the node
                property_keys = [
                    'name', 'description', 'phone', 'website', 'customer_id', 'type', 'additional_info',
                ]
                helpers.form_update_node(request.user, organization.handle_id, form, property_keys)
                # Set contacts
                contact_fields = DropdownModel.get('organization_contact_types').as_choices(empty=False)
                for field in contact_fields:
                    if field[0] in form.cleaned_data:
                        contact_data = form.cleaned_data[field[0]]
                        if contact_data:
                            if isinstance(contact_data, six.string_types):
                                if contact_data:
                                    helpers.create_contact_role_for_organization(request.user, organization, contact_data, field[1])
                            else:
                                helpers.link_contact_role_for_organization(request.user, organization, contact_data, field[1])

                # Set child organizations
                if form.cleaned_data['relationship_parent_of']:
                    organization_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent_of'])
                    helpers.set_parent_of(request.user, organization, organization_nh.handle_id)
                if form.cleaned_data['relationship_uses_a']:
                    procedure_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_uses_a'])
                    helpers.set_uses_a(request.user, organization, procedure_nh.handle_id)

                return { graphql_type.__name__.lower(): nh }
        else:
            # get the errors and return them
            raise GraphQLError('Form errors: {}'.format(form.errors))

    class NIMetaClass:
        django_form = EditOrganizationForm
        request_path   = '/'
        graphql_type   = Organization

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
    update_organization = UpdateNIOrganizationMutation.Field()
    delete_organization = NIOrganizationMutationFactory.get_delete_mutation().Field()

    delete_relationship = DeleteRelationship.Field()
