# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
from apps.noclook.forms import *
import apps.noclook.vakt.utils as sriutils
from apps.noclook.schema.types import *

from graphene import Field

logger = logging.getLogger(__name__)

## Organizations
class NICustomersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewCustomerForm
        update_form    = EditCustomerForm
        request_path   = '/'
        graphql_type   = Customer
        unique_node    = True

    class Meta:
        abstract = False


class NIEndUsersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewEndUserForm
        update_form    = EditEndUserForm
        request_path   = '/'
        graphql_type   = EndUser
        unique_node    = True

    class Meta:
        abstract = False


class NIProvidersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewProviderForm
        update_form    = EditProviderForm
        request_path   = '/'
        graphql_type   = Provider
        unique_node    = True

    class Meta:
        abstract = False


class NISiteOwnersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewSiteOwnerForm
        update_form    = EditSiteOwnerForm
        request_path   = '/'
        graphql_type   = SiteOwner
        unique_node    = True

    class Meta:
        abstract = False


## Cables and Equipment
class NIPortMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewPortForm
        update_form    = EditPortForm
        request_path   = '/'
        graphql_type   = Port
        create_exclude = ('relationship_parent', )
        update_exclude = ('relationship_parent', )

    class Meta:
        abstract = False


class NICableMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewCableForm
        update_form    = EditCableForm
        request_path   = '/'
        graphql_type   = Cable
        create_exclude = ('relationship_provider', )
        update_exclude = ('relationship_provider', )

    class Meta:
        abstract = False
