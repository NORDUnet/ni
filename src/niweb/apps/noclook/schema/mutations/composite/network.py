# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from ..network import *

class CompositePortMutation(CompositeMutation):
    class Input:
        pass

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.set_connected_to(user, slave_nh.get_node(), master_nh.handle_id)

    class NIMetaClass:
        graphql_type = Port
        graphql_subtype = Cable
        main_mutation_f = NIPortMutationFactory
        secondary_mutation_f = NICableMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('parent')


class CompositeCableMutation(CompositeMutation):
    class Input:
        pass

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.set_connected_to(user, master_nh.get_node(), slave_nh.handle_id)

    class NIMetaClass:
        graphql_type = Cable
        graphql_subtype = Port
        main_mutation_f = NICableMutationFactory
        secondary_mutation_f = NIPortMutationFactory
        context = sriutils.get_network_context()


class CompositeSwitchMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = Switch
        main_mutation_f = NISwitchMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('dependents')


class CompositeRouterMutation(CompositeMutation):
    class Input:
        pass

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.set_has(user, master_nh.get_node(), slave_nh.handle_id)

    class NIMetaClass:
        graphql_type = Router
        graphql_subtype = Port
        main_mutation_f = NIRouterMutationFactory
        secondary_mutation_f = NIPortMutationFactory
        context = sriutils.get_network_context()
        has_creation = False


class Owner(NIObjectType, RelationMixin):
    '''
    This type is a wrapper over all the owner entities present in network
    for DeleteOwnerMutation to be wrapped inside CompositeFirewallMutation.
    '''
    class NIMetaType:
        ni_type = 'Owner'
        ni_metatype = NIMETA_RELATION
        context_method = sriutils.get_network_context


class DeleteOwnerMutation(DeleteNIMutation):
    class NIMetaClass:
        graphql_type = Owner


class CompositeFirewallMutation(CompositeMutation):
    class Input:
        delete_owner = graphene.Field(DeleteOwnerMutation.Input)

    deleted_owner = graphene.Field(DeleteOwnerMutation)

    @classmethod
    def process_extra_subentities(cls, user, main_nh, root, info, input, context):
        ret_deleted_owner = None
        delete_owner_input = input.get("delete_owner")

        if delete_owner_input:
            ret_deleted_owner = DeleteOwnerMutation.mutate_and_get_payload(\
                root, info, **delete_owner_input)

        return dict(deleted_owner=ret_deleted_owner)

    class NIMetaClass:
        graphql_type = Firewall
        main_mutation_f = NIFirewallMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('dependents')
        has_creation = False


class CompositeExternalEquipmentMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = ExternalEquipment
        main_mutation_f = NIExternalEquipmentMutationFactory
        context = sriutils.get_network_context()
