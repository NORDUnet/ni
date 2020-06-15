# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
from apps.noclook.forms import *
from apps.noclook.models import SwitchType as SwitchTypeModel
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
    # check if there's a previous relation to ensure it's unique
    previous_rels = nodehandler.incoming.get('Provides', [])
    add_relation = False

    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        provider_id = form.cleaned_data[relation_name]

        if previous_rels:
            # check if it's the same provider
            relation = previous_rels[0]['relationship']

            # if it doesn't, delete the previous relation and create the new one
            previous_provider_id = relation.start_node.get('handle_id')

            if provider_id != str(previous_provider_id):
                relationship_id = previous_rels[0]['relationship_id']
                relationship = nc.get_relationship_model(
                    nc.graphdb.manager, relationship_id)
                relationship.delete()
                add_relation = True
        else:
            add_relation = True

        # finally add relation
        if add_relation:
            owner_nh = NodeHandle.objects.get(pk=provider_id)
            helpers.set_provider(request.user, nodehandler, owner_nh.handle_id)

    else: # delete previous relation as it comes empty
        if previous_rels:
            relationship_id = previous_rels[0]['relationship_id']
            relationship = nc.get_relationship_model(
                nc.graphdb.manager, relationship_id)
            relationship.delete()


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


def process_switch_type(request, form, nodehandler, relation_name):
    if relation_name in form.cleaned_data and form.cleaned_data[relation_name]:
        switch_type = SwitchTypeModel.objects.get(pk=form.cleaned_data[relation_name])
        helpers.dict_update_node(
            request.user, nodehandler.handle_id, {"model":switch_type.name})

        if switch_type.ports:
            for port in switch_type.ports.split(","):
                helpers.create_port(nodehandler, port.strip(), request.user)


class NISwitchMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewSwitchHostForm
        update_form    = EditSwitchForm
        graphql_type   = Switch
        unique_node    = True
        relations_processors = {
            'relationship_provider': process_provider,
            'switch_type': process_switch_type,
        }

    class Meta:
        abstract = False
