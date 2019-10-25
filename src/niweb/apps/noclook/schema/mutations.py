# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
import apps.noclook.vakt.utils as sriutils

from apps.noclook import activitylog, helpers
from apps.noclook.forms import *
from apps.noclook.models import Dropdown as DropdownModel, Role as RoleModel, DEFAULT_ROLES, Choice as ChoiceModel
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.test import RequestFactory
from django_comments.forms import CommentForm
from django_comments.models import Comment
from graphene import Field
from graphene_django.forms.mutation import DjangoModelFormMutation, BaseDjangoFormMutation
from django.core.exceptions import ObjectDoesNotExist

from .core import NIMutationFactory, CreateNIMutation, CommentType
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


def process_has_phone(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        contact_id = form.cleaned_data[relation_name]
        helpers.add_phone_contact(request.user, nodehandler, contact_id)


def process_has_email(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        contact_id = form.cleaned_data[relation_name]
        helpers.add_email_contact(request.user, nodehandler, contact_id)


def process_has_address(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        organization_id = form.cleaned_data[relation_name]
        helpers.add_address_organization(request.user, nodehandler, organization_id)


class NIPhoneMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form            = PhoneForm
        request_path    = '/'
        graphql_type    = Phone
        relations_processors = {
            'contact': process_has_phone,
        }
        property_update = ['name', 'type']

    class Meta:
        abstract = False


class NIEmailMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form            = EmailForm
        request_path    = '/'
        graphql_type    = Email

        relations_processors = {
            'contact': process_has_email,
        }
        property_update = ['name', 'type']

    class Meta:
        abstract = False


class NIAddressMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form            = AddressForm
        request_path    = '/'
        graphql_type    = Address

        relations_processors = {
            'organization': process_has_address,
        }
        property_update = ['name', 'website', 'phone', 'street', 'postal_code', 'postal_area']

    class Meta:
        abstract = False


def delete_outgoing_nodes(nodehandler, relation_name, user):
    node = nodehandler.get_node()
    relations = node.get_outgoing_relations()

    for relname, link_nodes in relations.items():
        if relname == relation_name:
            for link_node in link_nodes:
                link_node = link_node['node']
                helpers.delete_node(user, link_node.handle_id)


class NIContactMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form = EditContactForm
        request_path   = '/'
        graphql_type   = Contact
        relations_processors = {
            'relationship_works_for': process_works_for,
            'relationship_member_of': process_member_of,
        }

        delete_nodes = {
            'Has_email': delete_outgoing_nodes,
            'Has_phone': delete_outgoing_nodes,
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

        delete_nodes = {
            'Has_address': delete_outgoing_nodes,
        }

    class Meta:
        abstract = False

class CreateOrganization(CreateNIMutation):
    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()
        has_error      = False

        default_context = sriutils.get_default_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(request.user, default_context)

        if not authorized:
            raise GraphQLAuthException()

        # Get needed data from node
        if request.POST:
            form = form_class(request.POST.copy())
            if form.is_valid():
                try:
                    nh = helpers.form_to_generic_node_handle(request, form,
                            node_type, node_meta_type)
                except UniqueNodeError:
                    has_error = True
                    return has_error, [ErrorType(field="_", messages=["A {} with that name already exists.".format(node_type)])]

                # Generic node update
                # use property keys to avoid inserting contacts as a string property of the node
                property_keys = [
                    'name', 'description', 'customer_id', 'type', 'incident_management_info',
                    'affiliation_customer', 'affiliation_end_customer', 'affiliation_provider',
                    'affiliation_partner', 'affiliation_host_user', 'affiliation_site_owner'
                ]
                helpers.form_update_node(request.user, nh.handle_id, form, property_keys)
                nh_reload, organization = helpers.get_nh_node(nh.handle_id)

                # add default context
                NodeHandleContext(nodehandle=nh, context=default_context).save()

                # specific role setting
                for field, roledict in DEFAULT_ROLES.items():
                    if field in form.cleaned_data:
                        contact_id = form.cleaned_data[field]
                        role = RoleModel.objects.get(slug=field)
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
        is_create = True


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

        # check authorization
        authorized = sriutils.authorice_write_resource(request.user, handle_id)

        if not authorized:
            raise GraphQLAuthException()

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
                    'name', 'description', 'customer_id', 'type', 'incident_management_info',
                    'affiliation_customer', 'affiliation_end_customer', 'affiliation_provider',
                    'affiliation_partner', 'affiliation_host_user', 'affiliation_site_owner'
                ]
                helpers.form_update_node(request.user, organization.handle_id, form, property_keys)

                # specific role setting
                for field, roledict in DEFAULT_ROLES.items():
                    if field in form.cleaned_data:
                        contact_id = form.cleaned_data[field]
                        role = RoleModel.objects.get(slug=field)
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


class CreateRole(DjangoModelFormMutation):
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        default_context = sriutils.get_default_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, default_context)

        if not authorized:
            raise GraphQLAuthException()

        form = cls.get_form(root, info, **input)

        if form.is_valid():
            return cls.perform_mutate(form, info)
        else:
            errors = [
                ErrorType(field=key, messages=value)
                for key, value in form.errors.items()
            ]

            return cls(errors=errors)

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

        default_context = sriutils.get_default_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, default_context)

        if not authorized:
            raise GraphQLAuthException()

        try:
            role = RoleModel.objects.get(handle_id=handle_id)
            role.delete()
            success = True
        except ObjectDoesNotExist:
            success = False

        return DeleteRole(success=success, handle_id=handle_id)


class CreateComment(relay.ClientIDMutation):
    class Input:
        object_pk = graphene.Int(required=True)
        comment = graphene.String(required=True)

    comment = Field(CommentType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        default_context = sriutils.get_default_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, default_context)

        if not authorized:
            raise GraphQLAuthException()

        object_pk = input.get("object_pk",)
        comment = input.get("comment")
        content_type = ContentType.objects.get(app_label="noclook", model="nodehandle")

        request_factory = RequestFactory()
        request = request_factory.post('/', data={})
        site = get_current_site(request)

        comment = Comment(
            content_type=content_type,
            object_pk=object_pk,
            site=site,
            user=info.context.user,
            comment=comment,
        )
        comment.save()

        return CreateComment(comment=comment)

class UpdateComment(relay.ClientIDMutation):
    class Input:
        id = graphene.Int(required=True)
        comment = graphene.String(required=True)

    comment = Field(CommentType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        default_context = sriutils.get_default_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, default_context)

        if not authorized:
            raise GraphQLAuthException()

        id = input.get("id",)
        comment_txt = input.get("comment")

        comment = Comment.objects.get(id=id)
        comment.comment = comment_txt
        comment.save()

        return UpdateComment(comment=comment)

class DeleteComment(relay.ClientIDMutation):
    class Input:
        id = graphene.Int(required=True)

    success = graphene.Boolean(required=True)
    id = graphene.Int(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        default_context = sriutils.get_default_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, default_context)

        if not authorized:
            raise GraphQLAuthException()

        id = input.get("id", None)
        success = False

        try:
            comment = Comment.objects.get(id=id)
            comment.delete()
            success = True
        except ObjectDoesNotExist:
            success = False

        return DeleteComment(success=success, id=id)


class CreateOptionForDropdown(relay.ClientIDMutation):
    class Input:
        dropdown_name = graphene.String(required=True)
        name = graphene.String(required=True)
        value = graphene.String(required=True)

    choice = Field(Choice)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        default_context = sriutils.get_default_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(info.context.user, default_context)

        if not authorized:
            raise GraphQLAuthException()

        dropdown_name = input.get("dropdown_name")
        name  = input.get("name")
        value = input.get("value")
        dropdown = DropdownModel.objects.get(name=dropdown_name)

        choice = ChoiceModel(
            dropdown=dropdown,
            name=name,
            value=value
        )
        choice.save()

        return CreateOptionForDropdown(choice=choice)


class NOCRootMutation(graphene.ObjectType):
    create_group        = NIGroupMutationFactory.get_create_mutation().Field()
    update_group        = NIGroupMutationFactory.get_update_mutation().Field()
    delete_group        = NIGroupMutationFactory.get_delete_mutation().Field()

    create_procedure    = NIProcedureMutationFactory.get_create_mutation().Field()
    update_procedure    = NIProcedureMutationFactory.get_update_mutation().Field()
    delete_procedure    = NIProcedureMutationFactory.get_delete_mutation().Field()

    create_phone        = NIPhoneMutationFactory.get_create_mutation().Field()
    update_phone        = NIPhoneMutationFactory.get_update_mutation().Field()
    delete_phone        = NIPhoneMutationFactory.get_delete_mutation().Field()
    multiple_phone      = NIPhoneMutationFactory.get_multiple_mutation().Field()

    create_email        = NIEmailMutationFactory.get_create_mutation().Field()
    update_email        = NIEmailMutationFactory.get_update_mutation().Field()
    delete_email        = NIEmailMutationFactory.get_delete_mutation().Field()
    multiple_email      = NIEmailMutationFactory.get_multiple_mutation().Field()

    create_address      = NIAddressMutationFactory.get_create_mutation().Field()
    update_address      = NIAddressMutationFactory.get_update_mutation().Field()
    delete_address      = NIAddressMutationFactory.get_delete_mutation().Field()

    create_contact      = NIContactMutationFactory.get_create_mutation().Field()
    update_contact      = NIContactMutationFactory.get_update_mutation().Field()
    delete_contact      = NIContactMutationFactory.get_delete_mutation().Field()
    multiple_contact    = NIContactMutationFactory.get_multiple_mutation().Field()

    create_organization = CreateOrganization.Field()
    update_organization = UpdateOrganization.Field()
    delete_organization = NIOrganizationMutationFactory.get_delete_mutation().Field()

    create_role = CreateRole.Field()
    update_role = UpdateRole.Field()
    delete_role = DeleteRole.Field()

    create_comment = CreateComment.Field()
    update_comment = UpdateComment.Field()
    delete_comment = DeleteComment.Field()

    delete_relationship = DeleteRelationship.Field()
    create_option = CreateOptionForDropdown.Field()
