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


def process_provider(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        # check if there's a previous relation to ensure it's unique
        previous_rels = nodehandler.incoming.get('Provides', [])

        if previous_rels:
            relationship_id = previous_rels[0]['relationship_id']
            relationship = nc.get_relationship_model(nc.graphdb.manager, relationship_id)
            relationship.delete()

        owner_nh = NodeHandle.objects.get(pk=form.cleaned_data['relationship_provider'])
        helpers.set_provider(request.user, nodehandler, owner_nh.handle_id)


class NICableMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewCableForm
        update_form    = EditCableForm
        request_path   = '/'
        graphql_type   = Cable
        relations_processors = {
            'relationship_provider': process_provider,
        }

    class Meta:
        abstract = False
