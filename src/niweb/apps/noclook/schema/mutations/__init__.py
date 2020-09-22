# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from .common import *
from .community import *
from .network import *

from .composite.community import *
from .composite.network import *

class NOCRootMutation(graphene.ObjectType):
    ## Community mutations
    create_group        = NIGroupMutationFactory.get_create_mutation().Field()
    update_group        = NIGroupMutationFactory.get_update_mutation().Field()
    delete_group        = NIGroupMutationFactory.get_delete_mutation().Field()
    composite_group     = CompositeGroupMutation.Field()

    create_procedure    = NIProcedureMutationFactory.get_create_mutation().Field()
    update_procedure    = NIProcedureMutationFactory.get_update_mutation().Field()
    delete_procedure    = NIProcedureMutationFactory.get_delete_mutation().Field()

    create_phone        = NIPhoneMutationFactory.get_create_mutation().Field()
    update_phone        = NIPhoneMutationFactory.get_update_mutation().Field()
    delete_phone        = NIPhoneMutationFactory.get_delete_mutation().Field()

    create_email        = NIEmailMutationFactory.get_create_mutation().Field()
    update_email        = NIEmailMutationFactory.get_update_mutation().Field()
    delete_email        = NIEmailMutationFactory.get_delete_mutation().Field()

    create_address      = NIAddressMutationFactory.get_create_mutation().Field()
    update_address      = NIAddressMutationFactory.get_update_mutation().Field()
    delete_address      = NIAddressMutationFactory.get_delete_mutation().Field()

    create_contact      = NIContactMutationFactory.get_create_mutation().Field()
    update_contact      = NIContactMutationFactory.get_update_mutation().Field()
    delete_contact      = NIContactMutationFactory.get_delete_mutation().Field()
    composite_contact   = CompositeContactMutation.Field()

    create_organization    = CreateOrganization.Field()
    update_organization    = UpdateOrganization.Field()
    delete_organization    = NIOrganizationMutationFactory.get_delete_mutation().Field()
    composite_organization = CompositeOrganizationMutation.Field()

    create_role = CreateRole.Field()
    update_role = UpdateRole.Field()
    delete_role = DeleteRole.Field()

    ## Network mutations
    # Organizations
    create_customer = NICustomersMutationFactory.get_create_mutation().Field()
    update_customer = NICustomersMutationFactory.get_update_mutation().Field()
    delete_customer = NICustomersMutationFactory.get_delete_mutation().Field()

    create_endUser = NIEndUsersMutationFactory.get_create_mutation().Field()
    update_endUser = NIEndUsersMutationFactory.get_update_mutation().Field()
    delete_endUser = NIEndUsersMutationFactory.get_delete_mutation().Field()

    create_provider = NIProvidersMutationFactory.get_create_mutation().Field()
    update_provider = NIProvidersMutationFactory.get_update_mutation().Field()
    delete_provider = NIProvidersMutationFactory.get_delete_mutation().Field()

    create_siteOwner = NISiteOwnersMutationFactory.get_create_mutation().Field()
    update_siteOwner = NISiteOwnersMutationFactory.get_update_mutation().Field()
    delete_siteOwner = NISiteOwnersMutationFactory.get_delete_mutation().Field()

    # Cables and Equipment
    create_port = NIPortMutationFactory.get_create_mutation().Field()
    update_port = NIPortMutationFactory.get_update_mutation().Field()
    delete_port = NIPortMutationFactory.get_delete_mutation().Field()
    composite_port = CompositePortMutation.Field()

    create_cable = NICableMutationFactory.get_create_mutation().Field()
    update_cable = NICableMutationFactory.get_update_mutation().Field()
    delete_cable = NICableMutationFactory.get_delete_mutation().Field()
    composite_cable = CompositeCableMutation.Field()

    create_switch = NISwitchMutationFactory.get_create_mutation().Field()
    update_switch = NISwitchMutationFactory.get_update_mutation().Field()
    delete_switch = NISwitchMutationFactory.get_delete_mutation().Field()
    composite_switch = CompositeSwitchMutation.Field()

    update_router = NIRouterMutationFactory.get_update_mutation().Field()
    delete_router = NIRouterMutationFactory.get_delete_mutation().Field()
    composite_router = CompositeRouterMutation.Field()

    update_firewall = NIFirewallMutationFactory.get_update_mutation().Field()
    delete_firewall = NIFirewallMutationFactory.get_delete_mutation().Field()
    composite_firewall = CompositeFirewallMutation.Field()

    create_host = NIHostMutationFactory.get_create_mutation().Field()
    update_host = NIHostMutationFactory.get_update_mutation().Field()
    delete_host = NIHostMutationFactory.get_delete_mutation().Field()
    composite_host = CompositeHostMutation.Field()
    convert_host = ConvertHost.Field()

    create_externalEquipment = NIExternalEquipmentMutationFactory.get_create_mutation().Field()
    update_externalEquipment = NIExternalEquipmentMutationFactory.get_update_mutation().Field()
    delete_externalEquipment = NIExternalEquipmentMutationFactory.get_delete_mutation().Field()
    composite_externalEquipment = CompositeExternalEquipmentMutation.Field()

    create_opticalNode = NIOpticalNodeMutationFactory.get_create_mutation().Field()
    update_opticalNode = NIOpticalNodeMutationFactory.get_update_mutation().Field()
    delete_opticalNode = NIOpticalNodeMutationFactory.get_delete_mutation().Field()
    composite_opticalNode = CompositeOpticalNodeMutation.Field()

    create_oDF = NIODFMutationFactory.get_create_mutation().Field()
    update_oDF = NIODFMutationFactory.get_update_mutation().Field()
    delete_oDF = NIODFMutationFactory.get_delete_mutation().Field()
    composite_oDF = CompositeODFMutation.Field()

    ## Optical nodes
    create_opticalFilter = NIOpticalFilterMutationFactory.get_create_mutation().Field()
    update_opticalFilter = NIOpticalFilterMutationFactory.get_update_mutation().Field()
    delete_opticalFilter = NIOpticalFilterMutationFactory.get_delete_mutation().Field()
    composite_opticalFilter = CompositeOpticalFilterMutation.Field()

    create_opticalLink = NIOpticalLinkMutationFactory.get_create_mutation().Field()
    update_opticalLink = NIOpticalLinkMutationFactory.get_update_mutation().Field()
    delete_opticalLink = NIOpticalLinkMutationFactory.get_delete_mutation().Field()
    composite_opticalLink = CompositeOpticalLinkMutation.Field()

    create_opticalMultiplexSection = NIOpticalMultiplexSectionMutationFactory.get_create_mutation().Field()
    update_opticalMultiplexSection = NIOpticalMultiplexSectionMutationFactory.get_update_mutation().Field()
    delete_opticalMultiplexSection = NIOpticalMultiplexSectionMutationFactory.get_delete_mutation().Field()
    composite_opticalMultiplexSection = CompositeOpticalMultiplexSectionMutation.Field()

    create_opticalPath = NIOpticalPathMutationFactory.get_create_mutation().Field()
    update_opticalPath = NIOpticalPathMutationFactory.get_update_mutation().Field()
    delete_opticalPath = NIOpticalPathMutationFactory.get_delete_mutation().Field()
    composite_opticalPath = CompositeOpticalPathMutation.Field()

    ## Peering
    update_peeringPartner = NIPeeringPartnerMutationFactory.get_update_mutation().Field()
    delete_peeringPartner = NIPeeringPartnerMutationFactory.get_delete_mutation().Field()

    update_peeringGroup = NIPeeringGroupMutationFactory.get_update_mutation().Field()
    delete_peeringGroup = NIPeeringGroupMutationFactory.get_delete_mutation().Field()
    composite_peeringGroup = CompositePeeringGroupMutation.Field()

    ## Location
    create_site = NISiteMutationFactory.get_create_mutation().Field()
    update_site = NISiteMutationFactory.get_update_mutation().Field()
    delete_site = NISiteMutationFactory.get_delete_mutation().Field()
    composite_site = CompositeSiteMutation.Field()

    create_room = NIRoomMutationFactory.get_create_mutation().Field()
    update_room = NIRoomMutationFactory.get_update_mutation().Field()
    delete_room = NIRoomMutationFactory.get_delete_mutation().Field()
    composite_room = CompositeRoomMutation.Field()

    ## Common mutations
    create_comment = CreateComment.Field()
    update_comment = UpdateComment.Field()
    delete_comment = DeleteComment.Field()

    delete_relationship = DeleteRelationship.Field()
    create_option = CreateOptionForDropdown.Field()
