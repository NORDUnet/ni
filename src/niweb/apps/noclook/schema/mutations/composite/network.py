# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from ..network import *


## Equipment and cables
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

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.set_has(user, master_nh.get_node(), slave_nh.handle_id)

    class NIMetaClass:
        graphql_type = Switch
        graphql_subtype = Port
        main_mutation_f = NISwitchMutationFactory
        secondary_mutation_f = NIPortMutationFactory
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
    @classmethod
    def do_request(cls, request, **kwargs):
        post_copy = request.POST.copy()

        id              = request.POST.get('id')
        handle_id = relay.Node.from_global_id(id)[1]

        if not handle_id or \
            not NodeHandle.objects.filter(handle_id=handle_id).exists():

            has_error = True
            return has_error, [
                ErrorType(
                    field="_",
                    messages=["The node doesn't exist".format(node_type)]
                )
            ]

        nh, node = helpers.get_nh_node(handle_id)

        host_user_type = NodeType.objects.get_or_create(
                        type='Host User', slug='host-user')

        if nh.node_type == host_user_type:
            has_error = True
            return has_error, [
                ErrorType(
                    field="_",
                    messages=["Host Users can't be deleted".format(node_type)]
                )
            ]

        return super().do_request(request, **kwargs)

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
        graphql_type = ExternalEquipment
        main_mutation_f = NIExternalEquipmentMutationFactory
        context = sriutils.get_network_context()


class CompositeHostMutation(CompositeMutation):
    class Input:
        pass

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh):
        helpers.set_has(user, master_nh.get_node(), slave_nh.handle_id)

    @classmethod
    def can_process_subentities(cls, master_nh):
        '''
        Add ports only for physical hosts
        '''
        ret = False
        meta_type = master_nh.get_node().meta_type

        # check that the host is physical or do nothing
        if meta_type == 'Physical':
            ret = True

        return ret

    class NIMetaClass:
        graphql_type = Host
        graphql_subtype = Port
        main_mutation_f = NIHostMutationFactory
        secondary_mutation_f = NIPortMutationFactory
        ontext = sriutils.get_network_context()
        include_metafields = ('dependents')


class CompositeOpticalNodeMutation(CompositeMutation):
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
        graphql_type = OpticalNode
        main_mutation_f = NIOpticalNodeMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('has')


class CompositeODFMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = ODF
        main_mutation_f = NIODFMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('has')


## Optical Nodes
class CompositeOpticalFilterMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = OpticalFilter
        main_mutation_f = NIOpticalFilterMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('has')


class CompositeOpticalLinkMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = OpticalLink
        main_mutation_f = NIOpticalLinkMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('dependencies')


class CompositeOpticalMultiplexSectionMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = OpticalMultiplexSection
        main_mutation_f = NIOpticalMultiplexSectionMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('dependencies')


class CompositeOpticalPathMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = OpticalPath
        main_mutation_f = NIOpticalPathMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('dependencies')


## Peering
class CompositePeeringGroupMutation(CompositeMutation):
    class Input:
        pass

    class NIMetaClass:
        graphql_type = PeeringGroup
        main_mutation_f = NIPeeringGroupMutationFactory
        context = sriutils.get_network_context()
        include_metafields = ('dependencies')
        has_creation = False
