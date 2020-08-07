# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
from apps.noclook.forms import *
from apps.noclook.models import SwitchType as SwitchTypeModel
import apps.noclook.vakt.utils as sriutils
from apps.noclook.schema.types import *
from apps.noclook.views.edit import _nh_safe_get

from .common import get_unique_relation_processor

from graphene import Field
from binascii import Error as BinasciiError

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


class CreateHost(CreateNIMutation):
    @classmethod
    def do_request(cls, request, **kwargs):
        form_class = kwargs.get('form_class')
        nimetaclass = getattr(cls, 'NIMetaClass')
        graphql_type = getattr(nimetaclass, 'graphql_type')
        relations_processors = getattr(nimetaclass, 'relations_processors')
        nimetatype = getattr(graphql_type, 'NIMetaType')
        node_type = getattr(nimetatype, 'ni_type').lower()
        has_error = False

        context = sriutils.get_network_context()

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(request.user, context)

        if not authorized:
            raise GraphQLAuthException()

        # Get needed data from node
        if request.POST:
            # replace relay ids for handle_id in contacts if present
            post_data = request.POST.copy()

            relay_extra_ids = relations_processors.keys()
            for field in relay_extra_ids:
                handle_id = post_data.get(field)

                # check if it's already converted to int version
                try:
                    handle_id = int(handle_id)
                    continue
                except:
                    pass

                if handle_id:
                    try:
                        handle_id = relay.Node.from_global_id(handle_id)[1]
                        post_data.pop(field)
                        post_data.update({field: handle_id})
                    except BinasciiError:
                        pass # the id is already in handle_id format

            form = form_class(post_data)
            form.strict_validation = True

            if form.is_valid():
                data = form.cleaned_data
                if data['relationship_owner'] or data['relationship_location']:
                    meta_type = 'Physical'
                else:
                    meta_type = 'Logical'

                try:
                    nh = helpers.form_to_generic_node_handle(request, form,
                            node_type, meta_type, context)
                except UniqueNodeError:
                    has_error = True
                    return has_error, [ErrorType(field="_", messages=["A {} with that name already exists.".format(node_type)])]

                # Generic node update
                helpers.form_update_node(request.user, nh.handle_id, form)
                nh_reload, host_nh = helpers.get_nh_node(nh.handle_id)

                # add default context
                NodeHandleContext(nodehandle=nh, context=context).save()

                node = nh.get_node()

                # Set relations
                for relation_name, relation_f in relations_processors.items():
                    relation_f(request, form, node, relation_name)

                return has_error, { graphql_type.__name__.lower(): nh }
            else:
                # get the errors and return them
                has_error = True
                errordict = cls.format_error_array(form.errors)
                return has_error, errordict
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict

    class NIMetaClass:
        django_form = NewSRIHostForm
        request_path   = '/'
        graphql_type   = Host
        is_create = True

        relations_processors = {
            'relationship_owner': get_unique_relation_processor(
                'Owns',
                helpers.set_owner
            ),
            'responsible_group': get_unique_relation_processor(
                'Takes_responsibility',
                helpers.set_takes_responsibility
            ),
            'support_group': get_unique_relation_processor(
                'Supports',
                helpers.set_supports
            ),
        }


class EditHost(CreateNIMutation):
    @classmethod
    def do_request(cls, request, **kwargs):
        form_class = kwargs.get('form_class')
        nimetaclass = getattr(cls, 'NIMetaClass')
        graphql_type = getattr(nimetaclass, 'graphql_type')
        nimetatype = getattr(graphql_type, 'NIMetaType')
        node_type = getattr(nimetatype, 'ni_type').lower()
        relations_processors = getattr(nimetaclass, 'relations_processors')
        id = request.POST.get('id')
        has_error = False

        # check authorization
        handle_id = relay.Node.from_global_id(id)[1]
        authorized = sriutils.authorice_write_resource(request.user, handle_id)

        if not authorized:
            raise GraphQLAuthException()

        # Get needed data from node
        nh, host = helpers.get_nh_node(handle_id)
        relations = host.get_relations()
        out_relations = host.outgoing

        if request.POST:
            # set handle_id into POST data and remove relay id
            post_data = request.POST.copy()
            post_data.pop('id')
            post_data.update({'handle_id': handle_id})

            relay_extra_ids = relations_processors.keys()
            relay_extra_ids = (
                'relationship_user', 'relationship_owner',
                'relationship_depends_on', 'relationship_location',
                'relationship_location'
            )

            for field in relay_extra_ids:
                handle_id = post_data.get(field)
                if handle_id:
                    # check if it's already converted to int version
                    try:
                        handle_id = int(handle_id)
                        continue
                    except:
                        pass

                    try:
                        handle_id = relay.Node.from_global_id(handle_id)[1]
                        post_data.pop(field)
                        post_data.update({field: handle_id})
                    except BinasciiError:
                        pass # the id is already in handle_id format

            form = form_class(post_data)

            if form.is_valid():
                # Generic node update
                helpers.form_update_node(request.user, host.handle_id, form)

                # Set relations
                for relation_name, relation_f in relations_processors.items():
                    relation_f(request, form, host, relation_name)

                # You can not set location and depends on at the same time
                if form.cleaned_data['relationship_depends_on']:
                    depends_on_nh = _nh_safe_get(form.cleaned_data['relationship_depends_on'])
                    if depends_on_nh:
                        helpers.set_depends_on(request.user, host, depends_on_nh.handle_id)
                elif form.cleaned_data['relationship_location']:
                    _handle_location(request.user,
                                     host,
                                     form.cleaned_data['relationship_location'])
                if form.cleaned_data['services_locked'] and form.cleaned_data['services_checked']:
                    helpers.remove_rogue_service_marker(request.user, host.handle_id)

                return has_error, { graphql_type.__name__.lower(): nh }
            else:
                # get the errors and return them
                has_error = True
                errordict = cls.format_error_array(form.errors)
                return has_error, errordict
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict

    class NIMetaClass:
        django_form = EditSRIHostForm
        request_path   = '/'
        graphql_type   = Host
        is_create = False

        relations_processors = {
            'relationship_owner': get_unique_relation_processor(
                'Owns',
                helpers.set_owner
            ),
            'relationship_user': get_unique_relation_processor(
                'Uses',
                helpers.set_user
            ),
            'responsible_group': get_unique_relation_processor(
                'Takes_responsibility',
                helpers.set_takes_responsibility
            ),
            'support_group': get_unique_relation_processor(
                'Supports',
                helpers.set_supports
            ),
        }


class NIHostMutationFactory(NIMutationFactory):
    class NIMetaClass:
        create_form    = NewSRIHostForm
        update_form    = EditSRIHostForm
        graphql_type   = Host
        unique_node    = True
        relations_processors = {
            'relationship_owner': get_unique_relation_processor(
                'Owns',
                helpers.set_owner
            ),
            'responsible_group': get_unique_relation_processor(
                'Takes_responsibility',
                helpers.set_takes_responsibility
            ),
            'support_group': get_unique_relation_processor(
                'Supports',
                helpers.set_supports
            ),
        }

        manual_create = CreateHost
        manual_update = EditHost

    class Meta:
        abstract = False


class ConvertHost(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        slug = graphene.String(required=True)

    success = graphene.Boolean(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        id = input.get("id")
        slug = input.get("slug")
        success = False

        handle_id = relay.Node.from_global_id(id)[1]
        allowed_types = allowed_types_converthost # Types that can be added as Hosts by nmap
        user = info.context.user

        # check write permissions over host node
        authorized = sriutils.authorice_write_resource(user, handle_id)

        if not authorized:
            return ConvertHost(success=False)

        if NodeHandle.objects.filter(handle_id=handle_id).exists():
            nh = NodeHandle.objects.get(handle_id=handle_id)

            if slug in allowed_types and nh.node_type.type == 'Host':
                node_type = helpers.slug_to_node_type(slug, create=True)
                nh, node = helpers.logical_to_physical(user, handle_id)
                node.switch_type(nh.node_type.get_label(), node_type.get_label())
                nh.node_type = node_type
                nh.save()
                node_properties = {
                    'backup': ''
                }
                helpers.dict_update_node(
                    user, node.handle_id, node_properties, node_properties.keys())
                success = True

        return ConvertHost(success=success)


class NIPeeringPartnerMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form         = EditPeeringPartnerForm
        request_path = '/'
        graphql_type = PeeringPartner
        unique_node  = True

    class Meta:
        abstract = False


class NIPeeringGroupMutationFactory(NIMutationFactory):
    class NIMetaClass:
        form         = EditPeeringGroupForm
        request_path = '/'
        graphql_type = PeeringGroup
        unique_node  = True

    class Meta:
        abstract = False
