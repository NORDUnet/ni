# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
from apps.noclook.forms import *
from apps.noclook.models import SwitchType as SwitchTypeModel
import apps.noclook.vakt.utils as sriutils
from apps.noclook.schema.types import *

from .common import get_unique_relation_processor

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
        relations_processors = {
            'relationship_provider': get_unique_relation_processor(
                'Provides',
                helpers.set_provider
            ),
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
            'relationship_provider': get_unique_relation_processor(
                'Provides',
                helpers.set_provider
            ),
            'switch_type': process_switch_type,
            'responsible_group': get_unique_relation_processor(
                'Takes_responsibility',
                helpers.set_takes_responsibility
            ),
            'support_group': get_unique_relation_processor(
                'Supports',
                helpers.set_supports
            ),
        }

    class Meta:
        abstract = False


class NIRouterMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form    = EditRouterForm
        request_path   = '/'
        graphql_type   = Router
        relations_processors = {
            'relationship_location': get_unique_relation_processor(
                'Located_in',
                helpers.set_location
            ),
        }
        update_exclude = ('relationship_ports', )

    class Meta:
        abstract = False


class NIFirewallMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form    = EditFirewallNewForm
        graphql_type   = Firewall
        unique_node    = True
        relations_processors = {
            'relationship_provider': get_unique_relation_processor(
                'Provides',
                helpers.set_provider
            ),
            'switch_type': process_switch_type,
            'responsible_group': get_unique_relation_processor(
                'Takes_responsibility',
                helpers.set_takes_responsibility
            ),
            'support_group': get_unique_relation_processor(
                'Supports',
                helpers.set_supports
            ),
            'relationship_owner': get_unique_relation_processor(
                'Owns',
                helpers.set_owner
            ),
        }

    class Meta:
        abstract = False


class NIExternalEquipmentMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewExternalEquipmentForm
        update_form    = EditExternalEquipmentForm
        graphql_type   = ExternalEquipment
        unique_node    = True
        relations_processors = {
            'relationship_location': get_unique_relation_processor(
                'Located_in',
                helpers.set_location
            ),
            'relationship_owner': get_unique_relation_processor(
                'Owns',
                helpers.set_owner
            ),
        }

    class Meta:
        abstract = False
