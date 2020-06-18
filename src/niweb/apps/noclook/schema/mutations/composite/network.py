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
