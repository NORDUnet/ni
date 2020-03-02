# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from .common import *
from .community import *


class NOCRootMutation(graphene.ObjectType):
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

    create_comment = CreateComment.Field()
    update_comment = UpdateComment.Field()
    delete_comment = DeleteComment.Field()

    delete_relationship = DeleteRelationship.Field()
    create_option = CreateOptionForDropdown.Field()
