# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from ..community import *

class CompositeGroupMutation(CompositeMutation):
    class Input:
        pass

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.set_member_of(user, slave_nh.get_node(), master_nh.handle_id)

    class NIMetaClass:
        graphql_type = Group
        graphql_subtype = Contact
        main_mutation_f = NIGroupMutationFactory
        secondary_mutation_f = NIContactMutationFactory
        context = sriutils.get_community_context()


class CompositeOrganizationMutation(CompositeMutation):
    class Input:
        create_input = graphene.Field(CreateOrganization.Input)
        update_input = graphene.Field(UpdateOrganization.Input)

        create_subinputs = graphene.List(NIContactMutationFactory.get_create_mutation().Input)
        update_subinputs = graphene.List(NIContactMutationFactory.get_update_mutation().Input)
        delete_subinputs = graphene.List(NIContactMutationFactory.get_delete_mutation().Input)
        unlink_subinputs = graphene.List(DeleteRelationship.Input)

        create_address = graphene.List(NIAddressMutationFactory.get_create_mutation().Input)
        update_address = graphene.List(NIAddressMutationFactory.get_update_mutation().Input)
        delete_address = graphene.List(NIAddressMutationFactory.get_delete_mutation().Input)

    created = graphene.Field(CreateOrganization)
    updated = graphene.Field(UpdateOrganization)

    subcreated = graphene.List(NIContactMutationFactory.get_create_mutation())
    subupdated = graphene.List(NIContactMutationFactory.get_update_mutation())
    subdeleted = graphene.List(NIContactMutationFactory.get_delete_mutation())
    unlinked = graphene.List(DeleteRelationship)

    address_created = graphene.List(NIAddressMutationFactory.get_create_mutation())
    address_updated = graphene.List(NIAddressMutationFactory.get_update_mutation())
    address_deleted  = graphene.List(NIAddressMutationFactory.get_delete_mutation())

    @classmethod
    def get_link_kwargs(cls, master_input, slave_input):
        ret = {}
        role_id = slave_input.get('role_id', None)

        if role_id:
            ret['role_id'] = role_id

        return ret

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh, **kwargs):
        role_id = kwargs.get('role_id', None)
        role = None

        if role_id:
            role_handle_id = relay.Node.from_global_id(role_id)[1]
            role = RoleModel.objects.get(handle_id=role_handle_id)
        else:
            role = RoleModel.objects.get(slug=DEFAULT_ROLE_KEY)

        helpers.link_contact_role_for_organization(user, master_nh.get_node(), slave_nh.handle_id, role)

    @classmethod
    def link_address_to_organization(cls, user, master_nh, slave_nh, **kwargs):
        helpers.add_address_organization(user, slave_nh.get_node(), master_nh.handle_id)

    @classmethod
    def process_extra_subentities(cls, user, main_nh, root, info, input, context):
        extract_param = 'address'
        ret_subcreated = None
        ret_subupdated = None
        ret_subdeleted = None

        create_address = input.get("create_address")
        update_address = input.get("update_address")
        delete_address = input.get("delete_address")

        nimetaclass = getattr(cls, 'NIMetaClass')
        address_created = getattr(nimetaclass, 'address_created', None)
        address_updated = getattr(nimetaclass, 'address_updated', None)
        address_deleted = getattr(nimetaclass, 'address_deleted', None)

        main_handle_id = None

        if main_nh:
            main_handle_id = main_nh.handle_id

        if main_handle_id:
            if create_address:
                ret_subcreated = []

                for input in create_address:
                    input['context'] = context
                    ret = address_created.mutate_and_get_payload(root, info, **input)
                    ret_subcreated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_created = getattr(ret, extract_param, None)

                    if not sub_errors and sub_created:
                        helpers.add_address_organization(
                            user, sub_created.get_node(), main_handle_id)

            if update_address:
                ret_subupdated = []

                for input in update_address:
                    input['context'] = context
                    ret = address_updated.mutate_and_get_payload(root, info, **input)
                    ret_subupdated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_edited = getattr(ret, extract_param, None)

                    if not sub_errors and sub_edited:
                        helpers.add_address_organization(
                            user, sub_edited.get_node(), main_handle_id)

            if delete_address:
                ret_subdeleted = []

                for input in delete_address:
                    ret = address_deleted.mutate_and_get_payload(root, info, **input)
                    ret_subdeleted.append(ret)

        ret = dict(address_created=ret_subcreated,
                    address_updated=ret_subupdated,
                    address_deleted=ret_subdeleted)

        return ret

    class NIMetaClass:
        create_mutation = CreateOrganization
        update_mutation = UpdateOrganization
        create_submutation = NIContactMutationFactory.get_create_mutation()
        update_submutation = NIContactMutationFactory.get_update_mutation()
        delete_submutation = NIContactMutationFactory.get_delete_mutation()
        unlink_submutation = DeleteRelationship
        address_created = NIAddressMutationFactory.get_create_mutation()
        address_updated = NIAddressMutationFactory.get_update_mutation()
        address_deleted  = NIAddressMutationFactory.get_delete_mutation()
        graphql_type = Organization
        graphql_subtype = Contact
        context = sriutils.get_community_context()


class CompositeContactMutation(CompositeMutation):
    class Input:
        create_phones = graphene.List(NIPhoneMutationFactory.get_create_mutation().Input)
        update_phones = graphene.List(NIPhoneMutationFactory.get_update_mutation().Input)
        delete_phones = graphene.List(NIPhoneMutationFactory.get_delete_mutation().Input)

        link_rolerelations = graphene.List(RoleRelationMutation.Input)

    phones_created = graphene.List(NIPhoneMutationFactory.get_create_mutation())
    phones_updated = graphene.List(NIPhoneMutationFactory.get_update_mutation())
    phones_deleted = graphene.List(NIPhoneMutationFactory.get_delete_mutation())
    rolerelations = graphene.List(RoleRelationMutation)

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.add_email_contact(user, slave_nh.get_node(), master_nh.handle_id)

    @classmethod
    def process_extra_subentities(cls, user, main_nh, root, info, input, context):
        extract_param = 'phone'
        ret_subcreated = None
        ret_subupdated = None
        ret_subdeleted = None
        ret_rolerelations = None

        create_phones = input.get("create_phones")
        update_phones = input.get("update_phones")
        delete_phones = input.get("delete_phones")
        link_rolerelations = input.get("link_rolerelations")

        nimetaclass = getattr(cls, 'NIMetaClass')
        phones_created = getattr(nimetaclass, 'phones_created', None)
        phones_updated = getattr(nimetaclass, 'phones_updated', None)
        phones_deleted = getattr(nimetaclass, 'phones_deleted', None)
        rolerelation_mutation = getattr(nimetaclass, 'rolerelation_mutation', None)

        main_handle_id = None

        if main_nh:
            main_handle_id = main_nh.handle_id

        if main_handle_id:
            if create_phones:
                ret_subcreated = []

                for input in create_phones:
                    input['context'] = context
                    ret = phones_created.mutate_and_get_payload(root, info, **input)
                    ret_subcreated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_created = getattr(ret, extract_param, None)

                    if not sub_errors and sub_created:
                        helpers.add_phone_contact(
                            user, sub_created.get_node(), main_handle_id)

            if update_phones:
                ret_subupdated = []

                for input in update_phones:
                    input['context'] = context
                    ret = phones_updated.mutate_and_get_payload(root, info, **input)
                    ret_subupdated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_edited = getattr(ret, extract_param, None)

                    if not sub_errors and sub_edited:
                        helpers.add_phone_contact(
                            user, sub_edited.get_node(), main_handle_id)

            if delete_phones:
                ret_subdeleted = []

                for input in delete_phones:
                    ret = phones_deleted.mutate_and_get_payload(root, info, **input)
                    ret_subdeleted.append(ret)

            if link_rolerelations:
                ret_rolerelations = []

                for input in link_rolerelations:
                    input['contact_handle_id'] = main_handle_id
                    ret = rolerelation_mutation.mutate_and_get_payload(root, info, **input)
                    ret_rolerelations.append(ret)

        ret = dict(phones_created=ret_subcreated,
                    phones_updated=ret_subupdated,
                    phones_deleted=ret_subdeleted,
                    rolerelations=ret_rolerelations)

        return ret

    class NIMetaClass:
        phones_created = NIPhoneMutationFactory.get_create_mutation()
        phones_updated = NIPhoneMutationFactory.get_update_mutation()
        phones_deleted = NIPhoneMutationFactory.get_delete_mutation()
        rolerelation_mutation = RoleRelationMutation
        graphql_type = Contact
        graphql_subtype = Email
        main_mutation_f = NIContactMutationFactory
        secondary_mutation_f = NIEmailMutationFactory
        context = sriutils.get_community_context()
