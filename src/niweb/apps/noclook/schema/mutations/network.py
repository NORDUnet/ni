# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
from apps.noclook.forms import *
import apps.noclook.vakt.utils as sriutils
from apps.noclook.schema.types import *

from graphene import Field

logger = logging.getLogger(__name__)


class NICustomersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewCustomerForm
        update_form    = EditCustomerForm
        request_path   = '/'
        graphql_type   = Customer

    class Meta:
        abstract = False


class NIEndUsersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewEndUserForm
        update_form    = EditEndUserForm
        request_path   = '/'
        graphql_type   = EndUser

    class Meta:
        abstract = False


class NIProvidersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewProviderForm
        update_form    = EditProviderForm
        request_path   = '/'
        graphql_type   = Provider

    class Meta:
        abstract = False


class NISiteOwnersMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewSiteOwnerForm
        update_form    = EditSiteOwnerForm
        request_path   = '/'
        graphql_type   = SiteOwner

    class Meta:
        abstract = False
