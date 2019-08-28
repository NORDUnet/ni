# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc

from apps.noclook import activitylog, helpers
from apps.noclook.forms import *
from apps.noclook.models import Dropdown as DropdownModel, Role as RoleModel, DEFAULT_ROLES
from graphene_django.forms.mutation import DjangoModelFormMutation
from django.core.exceptions import ObjectDoesNotExist

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
    if relation_name in form.cleaned_data and 'role' in form.cleaned_data and \
        form.cleaned_data[relation_name] and form.cleaned_data['role']:

        organization_nh = NodeHandle.objects.get(pk=form.cleaned_data[relation_name])
        role_handle_id = form.cleaned_data['role']
        role = RoleModel.objects.get(handle_id=role_handle_id)
        helpers.set_works_for(request.user, nodehandler, organization_nh.handle_id, role.name)

def process_member_of(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
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

    class Meta:
        abstract = False


class UpdateOrganization(UpdateNIMutation):
    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()
        handle_id      = request.POST.get('handle_id')
        has_error      = False

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

                # specific role setting
                for field, roledict in DEFAULT_ROLES.items():
                    if field in form.cleaned_data:
                        contact_id = form.cleaned_data[field]
                        role = Role.objects.get(slug=field)
                        set_contact = helpers.get_contact_for_orgrole(organization.handle_id, role)

                        if contact_id:
                            if set_contact:
                                if set_contact.handle_id != contact_id:
                                    helpers.unlink_contact_with_role_from_org(request.user, organization, role)
                                    helpers.link_contact_role_for_organization(request.user, organization, contact_id, role)
                            else:
                                helpers.link_contact_role_for_organization(request.user, organization, contact_id, role)
                        elif set_contact:
                            helpers.unlink_contact_and_role_from_org(request.user, organization, set_contact.handle_id, role)

                # Set child organizations
                if form.cleaned_data['relationship_parent_of']:
                    organization_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_parent_of'])
                    helpers.set_parent_of(request.user, organization, organization_nh.handle_id)
                if form.cleaned_data['relationship_uses_a']:
                    procedure_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_uses_a'])
                    helpers.set_uses_a(request.user, organization, procedure_nh.handle_id)

                return has_error, { graphql_type.__name__.lower(): nh }
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict

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


class CreateRole(DjangoModelFormMutation):
    class Meta:
        form_class = NewRoleForm


class UpdateRole(DjangoModelFormMutation):
    class Input:
        handle_id = graphene.Int(required=True)

    @classmethod
    def get_form_kwargs(cls, root, info, **input):
        kwargs = {"data": input}

        pk = input.pop("handle_id", None)
        if pk:
            instance = cls._meta.model._default_manager.get(pk=pk)
            kwargs["instance"] = instance

        return kwargs

    class Meta:
        form_class = EditRoleForm


class DeleteRole(relay.ClientIDMutation):
    class Input:
        handle_id = graphene.Int(required=True)

    success = graphene.Boolean(required=True)
    handle_id = graphene.Int(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        handle_id = input.get("handle_id", None)
        success = False

        try:
            role = RoleModel.objects.get(handle_id=handle_id)
            role.delete()
            success = True
        except ObjectDoesNotExist:
            success = False

        return DeleteRole(success=success, handle_id=handle_id)


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
    update_organization = UpdateOrganization.Field()
    delete_organization = NIOrganizationMutationFactory.get_delete_mutation().Field()

    create_role = CreateRole.Field()
    update_role = UpdateRole.Field()
    delete_role = DeleteRole.Field()

    delete_relationship = DeleteRelationship.Field()
