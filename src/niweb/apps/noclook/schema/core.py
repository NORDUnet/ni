# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import datetime
import graphene
import logging
import norduniclient as nc
import re

import apps.noclook.vakt.utils as sriutils

from apps.noclook import activitylog, helpers
from apps.noclook.models import NodeType, NodeHandle, NodeHandleContext
from collections import OrderedDict, Iterable
from django import forms
from django.contrib.auth.models import User as DjangoUser
from django.forms.utils import ValidationError
from django.test import RequestFactory
from django.utils.text import slugify
from django_comments.models import Comment
from graphene import relay
from graphene.types import Scalar, DateTime
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions, ErrorType
from graphql import GraphQLError
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible
from norduniclient import META_TYPES

from .scalars import *
from .fields import *
from .querybuilders import *
from .metatypes import *
from ..models import NodeType, NodeHandle

logger = logging.getLogger(__name__)

########## RELATION AND NODE TYPES
NIMETA_LOGICAL  = META_TYPES[1]
NIMETA_RELATION = META_TYPES[2]
NIMETA_PHYSICAL = META_TYPES[0]
NIMETA_LOCATION = META_TYPES[3]

metatype_interfaces = OrderedDict([
    (NIMETA_LOGICAL,  { 'interface': Logical,  'mixin':  LogicalMixin, } ),
    (NIMETA_RELATION, { 'interface': Relation, 'mixin':  RelationMixin, }),
    (NIMETA_PHYSICAL, { 'interface': Physical, 'mixin':  PhysicalMixin, }),
    (NIMETA_LOCATION, { 'interface': Location, 'mixin':  LocationMixin, }),
])

# association dict between interface and mixin
subclasses_interfaces = OrderedDict([
    (Logical, []),
    (Relation, []),
    (Physical, []),
    (Location, []),
])

class User(DjangoObjectType):
    '''
    The django user type
    '''
    class Meta:
        model = DjangoUser
        only_fields = ['id', 'username', 'first_name', 'last_name', 'email']


class UserInputType(graphene.InputObjectType):
    '''
    This object represents an input for an user used in connections
    '''
    username = graphene.String(required=True)


class NINodeHandlerType(DjangoObjectType):
    '''
    Generic NodeHandler graphene type
    '''
    class Meta:
        model = NodeHandle
        interfaces = (relay.Node, )


class NIRelationType(graphene.ObjectType):
    '''
    This class represents a relationship and its properties
    '''
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        **options,
    ):
        super(NIRelationType, cls).__init_subclass_with_meta__(
            **options
        )

    relation_id = graphene.Int(required=True)
    type = graphene.String(required=True) # this may be set to an Enum
    start = graphene.Field(NINodeHandlerType, required=True)
    end = graphene.Field(NINodeHandlerType, required=True)
    nidata = graphene.List(DictEntryType)

    def resolve_relation_id(self, info, **kwargs):
        self.relation_id = self.id

        return self.relation_id

    def resolve_nidata(self, info, **kwargs):
        '''
        Is just the same than old resolve_nidata, but it doesn't resolve the node
        '''
        ret = []

        alldata = self.data
        for key, value in alldata.items():
            if key and value:
                ret.append(DictEntryType(name=key, value=value))

        return ret

    def resolve_start(self, info, **kwargs):
        return NodeHandle.objects.get(handle_id=self.start['handle_id'])

    def resolve_end(self, info, **kwargs):
        return NodeHandle.objects.get(handle_id=self.end['handle_id'])

    @classmethod
    def get_filter_input_fields(cls):
        '''
        Method used by build_filter_and_order for a Relation type
        '''
        input_fields = {}
        classes = NIRelationType, cls

        ni_metatype    = getattr(cls, 'NIMetaType')
        filter_include = getattr(ni_metatype, 'filter_include', None)
        filter_exclude = getattr(ni_metatype, 'filter_exclude', None)

        if filter_include and filter_exclude:
            raise Exception("Only filter_include or filter_include metafields can be defined on {}".format(cls))

        # add type NIRelationType and subclass
        for clz in classes:
            for name, field in clz.__dict__.items():
                if field:
                    add_field = False

                    if isinstance(field, graphene.types.scalars.String) or\
                        isinstance(field, graphene.types.scalars.Int):
                        add_field = True

                    if filter_include:
                        if name not in filter_include:
                            add_field = False
                    elif filter_exclude:
                        if name in filter_exclude:
                            add_field = False

                    if add_field:
                        input_field = type(field)
                        input_fields[name] = input_field

        return input_fields

    @classproperty
    def match_additional_clause(cls):
        nimetatype = getattr(cls, 'NIMetaType', None)
        relation_name = ''
        if nimetatype:
            relation_name = nimetatype.nimodel.RELATION_NAME

        if relation_name:
            relation_name = ':{}'.format(relation_name)

        return "({})-[{}{}{}]-({})".format('{}', cls.neo4j_var_name, '{}', relation_name, '{}')

    neo4j_var_name = "r"

    class Meta:
        interfaces = (relay.Node, )


class DictRelationType(graphene.ObjectType):
    '''
    This type represents an key value pair for a relationship dictionary,
    the key is the name of the relationship and the value the NIRelationType itself
    '''
    name = graphene.String(required=True)
    relation = graphene.Field(NIRelationType, required=True)


class CommentType(DjangoObjectType):
    '''
    This type represents a comment in the API, it uses the comments model just
    like the rest of noclook
    '''
    object_id = graphene.ID(required=True)

    def resolve_object_id(self, info, **kwargs):
        node = NodeHandle.objects.get(handle_id = self.object_pk)
        object_id = relay.Node.to_global_id(str(node.node_type),
                                            str(self.object_pk))

        return object_id

    class Meta:
        model = Comment
        interfaces = (relay.Node, )


class NINodeType(DjangoObjectType):
    '''
    Simple NodeType graphene class
    '''
    class Meta:
        model = NodeType
        exclude_fields = ['nodehandle_set']


input_fields_clsnames = {}


class NIObjectType(DjangoObjectType):
    '''
    This class expands graphene_django object type adding the defined fields in
    the types subclasses and extracts the data from the norduniclient nodes and
    adds a resolver for each field, a nidata field is also added to hold the
    values of the node data dict.
    '''

    filter_names = None

    _connection_input = None
    _connection_order = None
    _order_field_match = None
    _asc_suffix = 'ASC'
    _desc_suffix = 'DESC'

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        **options,
    ):
        allfields = cls.__dict__
        graphfields = OrderedDict()

        # getting all not magic attributes, also filter non NI fields
        for name, field in allfields.items():
            pattern = re.compile("^__.*__$")
            is_nibasicfield = issubclass(field.__class__, NIBasicField)
            if pattern.match(name) or callable(field) or not is_nibasicfield:
                continue
            graphfields[name] = field

        # run over the fields defined and adding graphene fields and resolvers
        for name, field in graphfields.items():
            field_fields = field.__dict__

            field_type      = field_fields.get('field_type')
            manual_resolver = field_fields.get('manual_resolver')
            type_kwargs     = field_fields.get('type_kwargs')
            type_args       = field_fields.get('type_args')
            rel_name        = field_fields.get('rel_name')
            rel_method      = field_fields.get('rel_method')
            not_null_list   = field_fields.get('not_null_list')
            dropdown_name   = field_fields.get('dropdown_name')

            # adding the field
            field_value = None

            if not isinstance(field, ComplexField):
                if type_kwargs:
                    field_value = field_type(**type_kwargs)
                elif type_args:
                    field_value = field_type(*type_args)
                    if not_null_list:
                        field_value = graphene.NonNull(field_type(*type_args))
                else:
                    field_value = field_type(**{})
            else:
                field_value = graphene.Field(field.get_field_type())

            setattr(cls, name, field_value)

            # adding the resolver
            if not manual_resolver:
                setattr(cls, 'resolve_{}'.format(name), \
                    field.get_resolver(
                        field_name=name,
                        rel_name=rel_name,
                        rel_method=rel_method,
                        dropdown_name=dropdown_name,
                    )
                )

            elif callable(manual_resolver):
                setattr(cls, 'resolve_{}'.format(name), manual_resolver)
            else:
                raise Exception(
                    'NIObjectField manual_resolver must be a callable in field {}'\
                        .format(name)
                )

        # add meta types interfaces if present
        interfaces = [NINode, ]
        metatype_interface = cls.get_metatype_interface()

        if metatype_interface:
            interfaces.append(metatype_interface)

            # add also this class to the subclasses list
            subclasses_interfaces[metatype_interface].append(cls)

        options['model'] = NIObjectType._meta.model
        options['interfaces'] = interfaces

        # init mutations inner attributes (to be filled by the mutation factory)
        setattr(cls, 'create_mutation', None)
        setattr(cls, 'update_mutation', None)
        setattr(cls, 'delete_mutation', None)

        super(NIObjectType, cls).__init_subclass_with_meta__(
            **options
        )

    nidata = graphene.List(DictEntryType, resolver=resolve_nidata)

    incoming = graphene.List(DictRelationType)
    outgoing = graphene.List(DictRelationType)
    comments = graphene.List(CommentType)

    @classmethod
    def get_metatype_interface(cls):
        metatype_interface = None

        if hasattr(cls, 'NIMetaType'):
            ni_metatype = cls.get_from_nimetatype("ni_metatype")
            if ni_metatype in metatype_interfaces:
                metatype_interface = metatype_interfaces[ni_metatype]['interface']

        return metatype_interface

    def resolve_incoming(self, info, **kwargs):
        '''
        Resolver for incoming relationships for the node
        '''
        incoming_rels = self.get_node().incoming
        ret = []
        for rel_name, rel_list in incoming_rels.items():
            for rel in rel_list:
                relation_id = rel['relationship_id']
                relation_model = nc.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
                ret.append(DictRelationType(name=rel_name, relation=relation_model))

        return ret

    def resolve_outgoing(self, info, **kwargs):
        '''
        Resolver for outgoing relationships for the node
        '''
        outgoing_rels = self.get_node().outgoing
        ret = []
        for rel_name, rel_list in outgoing_rels.items():
            for rel in rel_list:
                relation_id = rel['relationship_id']
                rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
                ret.append(DictRelationType(name=rel_name, relation=rel))

        return ret

    def resolve_comments(self, info, **kwargs):
        handle_id = self.handle_id
        return Comment.objects.filter(object_pk=handle_id)

    @classmethod
    def get_from_nimetatype(cls, attr):
        ni_metatype = getattr(cls, 'NIMetaType', None)
        return getattr(ni_metatype, attr)

    @classmethod
    def get_type_name(cls):
        ni_type = cls.get_from_nimetatype('ni_type')
        node_type = NodeType.objects.filter(type=ni_type).first()
        return node_type.type

    @classmethod
    def get_type_context(cls):
        context_resolver = cls.get_from_nimetatype('context_method')

        if not context_resolver:
            context_resolver = sriutils.get_default_context

        return context_resolver()

    @classmethod
    def get_create_mutation(cls):
        return cls.create_mutation

    @classmethod
    def set_create_mutation(cls, create_mutation):
        cls.create_mutation = create_mutation

    @classmethod
    def get_update_mutation(cls):
        return cls.update_mutation

    @classmethod
    def set_update_mutation(cls, update_mutation):
        cls.update_mutation = update_mutation

    @classmethod
    def get_delete_mutation(cls):
        return cls.delete_mutation

    @classmethod
    def set_delete_mutation(cls, delete_mutation):
        cls.delete_mutation = delete_mutation

    @classmethod
    def get_filter_input_fields(cls):
        '''
        Method used by build_filter_and_order for a Node type
        '''
        input_fields = {}

        ni_metatype    = getattr(cls, 'NIMetaType')
        filter_include = getattr(ni_metatype, 'filter_include', None)
        filter_exclude = getattr(ni_metatype, 'filter_exclude', None)

        for name, field in cls.__dict__.items():
            # string or string like fields
            if field:
                if isinstance(field, graphene.types.scalars.String) or\
                    isinstance(field, graphene.types.scalars.Int) or\
                    isinstance(field, graphene.types.scalars.Boolean) or\
                    isinstance(field, ChoiceScalar):
                    input_field = type(field)
                    input_fields[name] = input_field
                elif isinstance(field, graphene.types.structures.List):
                    # create arguments for input_field
                    field_of_type = field._of_type

                    # recase to lower camelCase
                    name_fot = field_of_type.__name__
                    components = name_fot.split('_')
                    name_fot = components[0] + ''.join(x.title() for x in components[1:])

                    # get object attributes by their filter input fields
                    # to build the filter field for the nested object
                    filter_attrib = {}
                    instance_inputfield = False

                    if hasattr(field_of_type, 'get_filter_input_fields'):
                        instance_inputfield = True
                        for a, b in field_of_type.get_filter_input_fields().items():
                            if callable(b):
                                filter_attrib[a] = b()
                            else:
                                filter_attrib[a] = b[0]()

                    filter_attrib['_of_type'] = field._of_type

                    if instance_inputfield:
                        ifield_clsname = '{}InputField'.format(name_fot)

                        if not ifield_clsname in input_fields_clsnames:
                            binput_field = type(ifield_clsname, (graphene.InputObjectType, ), filter_attrib)
                            input_fields_clsnames[ifield_clsname] = binput_field
                        else:
                            binput_field = input_fields_clsnames[ifield_clsname]

                        input_fields[name] = binput_field, field._of_type
                elif isinstance(field, graphene.types.field.Field) and\
                    field.type == Choice:
                    input_fields[name] = ChoiceScalar

        input_fields['id'] = graphene.ID

        # add 'created' and 'modified' datetime fields
        for date_ffield in DateQueryBuilder.fields:
            input_fields[date_ffield] = DateTime

        # add 'creator' and 'modifier' user fields
        for user_ffield in UserQueryBuilder.fields:
            input_fields[user_ffield] = UserInputType

        return input_fields

    @classmethod
    def build_filter_and_order(cls):
        '''
        This method generates a Filter and Order object from the class itself
        to be used in filtering connections
        '''
        if cls._connection_input and cls._connection_order:
            return cls._connection_input, cls._connection_order

        ni_type = cls.get_from_nimetatype('ni_type').replace(' ', '')

        # build filter input class and order enum
        filter_attrib = {}
        cls.filter_names = {}
        cls._order_field_match = {}
        enum_options = []
        input_fields = cls.get_filter_input_fields()

        for field_name, input_field in input_fields.items():
            # creating field instance
            field_instance = None
            the_field = None

            # is a plain scalar field?
            if not isinstance(input_field, Iterable):
                field_instance = input_field()
                the_field = input_field
                of_type = input_field

            else: # it must be a list other_node
                field_instance = input_field[0]()
                the_field = input_field[0]
                of_type = input_field[1]

            # adding order attributes and store in field property
            if of_type == graphene.Int or \
                of_type == graphene.String or \
                of_type == ChoiceScalar or \
                issubclass(of_type, DateTime) or \
                issubclass(of_type, NIObjectType) or \
                issubclass(of_type, NIRelationType):
                asc_field_name = '{}_{}'.format(field_name, cls._asc_suffix)
                desc_field_name = '{}_{}'.format(field_name, cls._desc_suffix)
                enum_options.append([asc_field_name, asc_field_name])
                enum_options.append([desc_field_name, desc_field_name])

                cls._order_field_match[asc_field_name] = {
                    'field': field_name,
                    'is_desc': False,
                    'input_field': of_type,
                }
                cls._order_field_match[desc_field_name] = {
                    'field': field_name,
                    'is_desc': True,
                    'input_field': of_type,
                }

            # adding filter attributes
            for suffix, suffix_attr in AbstractQueryBuilder.filter_array.items():
                # filter field naming
                if not suffix == '':
                    suffix = '_{}'.format(suffix)

                fmt_filter_field = '{}{}'.format(field_name, suffix)

                if not suffix_attr['only_strings'] \
                    or isinstance(field_instance, graphene.String) \
                    or isinstance(field_instance, ChoiceScalar) \
                    or isinstance(field_instance, graphene.InputObjectType):
                    if 'wrapper_field' not in suffix_attr or not suffix_attr['wrapper_field']:
                        filter_attrib[fmt_filter_field] = field_instance
                        cls.filter_names[fmt_filter_field]  = {
                            'field' : field_name,
                            'suffix': suffix,
                            'field_type': field_instance,
                        }
                    else:
                        wrapped_field = the_field
                        for wrapper_field in suffix_attr['wrapper_field']:
                            wrapped_field = wrapper_field(wrapped_field)

                        filter_attrib[fmt_filter_field] = wrapped_field
                        cls.filter_names[fmt_filter_field]  = {
                            'field' : field_name,
                            'suffix': suffix,
                            'field_type': field_instance,
                        }

        simple_filter_input = type('{}NestedFilter'.format(ni_type), (graphene.InputObjectType, ), filter_attrib)

        filter_attrib = {}
        filter_attrib['AND'] = graphene.List(graphene.NonNull(simple_filter_input))
        filter_attrib['OR'] = graphene.List(graphene.NonNull(simple_filter_input))

        filter_input = type('{}Filter'.format(ni_type), (graphene.InputObjectType, ), filter_attrib)

        # add the handle id field manually
        handle_id_field = 'handle_id'
        asc_field_name = '{}_{}'.format(handle_id_field, cls._asc_suffix)
        desc_field_name = '{}_{}'.format(handle_id_field, cls._desc_suffix)
        enum_options.append([asc_field_name, asc_field_name])
        enum_options.append([desc_field_name, desc_field_name])

        orderBy = graphene.Enum('{}OrderBy'.format(ni_type), enum_options)

        # store the created objects
        cls._connection_input = filter_input
        cls._connection_order = orderBy

        return filter_input, orderBy

    @classmethod
    def get_byid_resolver(cls):
        '''
        This method returns a generic by id resolver for every nodetype in NOCAutoQuery
        '''
        type_name = cls.get_type_name()

        def generic_byid_resolver(self, info, **args):
            id = args.get('id')
            handle_id = None
            ret = None

            try:
                _type, handle_id = relay.Node.from_global_id(id)
            except:
                # we'll return None
                handle_id = None

            node_type = NodeType.objects.get(type=type_name)
            ret = None

            if info.context and info.context.user.is_authenticated:
                if handle_id:
                    authorized = sriutils.authorice_read_resource(
                        info.context.user, handle_id
                    )

                    if authorized:
                        try:
                            int_id = str(handle_id)
                            ret = NodeHandle.objects.filter(node_type=node_type).get(handle_id=int_id)
                        except ValueError:
                            ret = NodeHandle.objects.filter(node_type=node_type).get(handle_id=handle_id)
                    else:
                        # 403
                        pass
                else:
                    raise GraphQLError('A handle_id must be provided')

                return ret
            else:
                # 401
                raise GraphQLAuthException()

        return generic_byid_resolver

    @classmethod
    def get_list_resolver(cls):
        '''
        This method returns a simple list resolver for every nodetype in NOCAutoQuery
        '''
        type_name = cls.get_type_name()

        def generic_list_resolver(self, info, **args):
            qs = NodeHandle.objects.none()

            if info.context and info.context.user.is_authenticated:
                context = cls.get_type_context()
                authorized = sriutils.authorize_list_module(
                    info.context.user, context
                )

                if authorized:
                    node_type = NodeType.objects.get(type=type_name)
                    qs = NodeHandle.objects.filter(node_type=node_type).order_by('node_name')

                    # the node list is trimmed to the nodes that the user can read
                    qs = sriutils.trim_readable_queryset(qs, info.context.user)
                else:
                    # 403
                    pass
            else:
                # 401
                raise GraphQLAuthException()

            return qs

        return generic_list_resolver

    @classmethod
    def get_count_resolver(cls):
        '''
        This method returns a simple list resolver for every nodetype in NOCAutoQuery
        '''
        type_name = cls.get_type_name()

        def generic_count_resolver(self, info, **args):
            qs = NodeHandle.objects.none()

            if info.context and info.context.user.is_authenticated:
                context = cls.get_type_context()
                authorized = sriutils.authorize_list_module(
                    info.context.user, context
                )

                if authorized:
                    node_type = NodeType.objects.get(type=type_name)
                    qs = NodeHandle.objects.filter(node_type=node_type).order_by('node_name')

                    # the node list is trimmed to the nodes that the user can read
                    qs = sriutils.trim_readable_queryset(qs, info.context.user)
                else:
                    # 403
                    pass
            else:
                # 401
                raise GraphQLAuthException()

            return qs.count()

        return generic_count_resolver

    @classmethod
    def filter_is_empty(cls, filter):
        empty = False

        if not filter:
            empty = True

        if not empty and filter:
            and_portion = None
            if 'AND' in filter:
                and_portion = filter['AND']

            or_portion = None
            if 'OR' in filter:
                or_portion = filter['OR']

            if not and_portion and not or_portion:
                empty = True
            elif not (and_portion and and_portion[0])\
             and not (or_portion and or_portion[0]):
                empty = True

        return empty

    @classmethod
    def order_is_empty(cls, orderBy):
        empty = False

        if not orderBy:
            empty = True

        return empty

    @classmethod
    def get_connection_resolver(cls):
        '''
        This method returns a generic connection resolver for every nodetype in NOCAutoQuery
        '''
        type_name = cls.get_type_name()

        def generic_list_resolver(self, info, **args):
            '''
            The idea for the connection resolver is to filter the whole NodeHandle
            queryset using the date and users in the filter input, but also
            the neo4j attributes exposed in the api.

            Likewise, the ordering of it is based in neo4j attributes, so in
            order to return an ordered node collection we have to query each
            node by its handle_id and append to a list.
            '''
            ret = NodeHandle.objects.none()
            filter  = args.get('filter', None)
            orderBy = args.get('orderBy', None)

            apply_handle_id_order = False
            revert_default_order = False
            use_neo4j_query = False

            context = cls.get_type_context()

            if info.context and info.context.user.is_authenticated:
                if sriutils.authorize_list_module(info.context.user, context):
                    # filtering will take a different approach
                    nodes = None

                    if NodeType.objects.filter(type=type_name):
                        node_type = NodeType.objects.get(type=type_name)
                        qs = NodeHandle.objects.filter(node_type=node_type)

                        # instead of vakt here, we reduce the original qs
                        # to only the ones the user has right to read
                        qs = sriutils.trim_readable_queryset(qs, info.context.user)

                        # remove default ordering prop if there's no filter
                        if not cls.order_is_empty(orderBy):
                            if orderBy == 'handle_id_DESC':
                                orderBy = None
                                apply_handle_id_order = True
                                revert_default_order = False
                            elif orderBy == 'handle_id_ASC':
                                orderBy = None
                                apply_handle_id_order = True
                                revert_default_order = True

                        qs_order_prop = None
                        qs_order_order = None

                        if not cls.order_is_empty(orderBy):
                            m = re.match(r"([\w|\_]*)_(ASC|DESC)", orderBy)
                            prop = m[1]
                            order = m[2]

                            if prop in DateQueryBuilder.fields:
                                # set model attribute ordering
                                qs_order_prop  = prop
                                qs_order_order = order

                        if not cls.filter_is_empty(filter) or not cls.order_is_empty(orderBy):
                            # filter queryset with dates and users
                            qs = DateQueryBuilder.filter_queryset(filter, qs)
                            qs = UserQueryBuilder.filter_queryset(filter, qs)

                            # remove order if is a date order
                            if qs_order_prop and qs_order_order:
                                orderBy = None

                            # get filter clause
                            readable_ids = sriutils.get_ids_user_canread(info.context.user)

                            # create query
                            fmt_type_name = type_name.replace(' ', '_')

                            q = cls.build_filter_query(filter, orderBy, fmt_type_name,
                                            apply_handle_id_order, revert_default_order,
                                            readable_ids)
                            nodes = nc.query_to_list(nc.graphdb.manager, q)
                            nodes = [ node['n'] for node in nodes]

                            use_neo4j_query = True
                        else:
                            use_neo4j_query = False

                        if use_neo4j_query:
                            ret = []

                            handle_ids = []
                            for node in nodes:
                                if node['handle_id'] not in handle_ids:
                                    handle_ids.append(node['handle_id'])

                            for handle_id in handle_ids:
                                nodeqs = qs.filter(handle_id=handle_id)
                                try:
                                    the_node = nodeqs.first()
                                    if the_node:
                                        ret.append(the_node)
                                except:
                                    pass # nothing to do if the qs doesn't have elements

                            # apply date order if it applies
                            if qs_order_prop and qs_order_order:
                                reverse = True if qs_order_order == 'DESC' else False
                                ret.sort(key=lambda x: getattr(x, qs_order_prop, ''), reverse=reverse)
                        else:
                            # do nodehandler attributes ordering now that we have
                            # the nodes set, if this order is requested
                            if qs_order_prop and qs_order_order:
                                reverse = True if qs_order_order == 'DESC' else False

                                if reverse:
                                    qs = qs.order_by('{}'.format(qs_order_prop))
                                else:
                                    qs = qs.order_by('-{}'.format(qs_order_prop))

                            if apply_handle_id_order:
                                logger.debug('Apply handle_id order')

                                if not revert_default_order:
                                    logger.debug('Apply descendent handle_id')
                                    qs = qs.order_by('-handle_id')
                                else:
                                    logger.debug('Apply ascending handle_id')
                                    qs = qs.order_by('handle_id')

                            ret = list(qs)
                else:
                    # 403
                    pass
            else:
                # 401
                raise GraphQLAuthException()

            if not ret:
                ret = []

            return ret

        return generic_list_resolver

    @classmethod
    def build_filter_query(cls, filter, orderBy, nodetype,\
        handle_id_order=False, revert_order=False, readable_ids=None):
        build_query = ''
        order_query = ''
        optional_matches = ''

        operations = {
            'AND': {
                'filters': [],
                'predicates': [],
            },
            'OR': {
                'filters': [],
                'predicates': [],
            },
        }

        # build AND block
        and_filters = []
        and_predicates = []

        if filter and 'AND' in filter:
            and_filters = filter.get('AND', [])
            operations['AND']['filters'] = and_filters

        # build OR block
        or_filters = []
        or_predicates = []

        if filter and 'OR' in filter:
            or_filters = filter.get('OR', [])
            operations['OR']['filters'] = or_filters

        # additional clauses
        match_additional_nodes = []
        match_additional_rels  = []

        and_node_predicates = []
        and_rels_predicates = []

        raw_additional_clause = {}

        # neo4j vars dict
        neo4j_vars = {}

        # embed entity index
        idxdict = {
            'rel_idx': 1,
            'node_idx': 1,
            'subnode_idx': 1,
            'subrel_idx': 1,
        }

        filtered_fields = []

        if filter:
            for operation in operations.keys():
                filters = operations[operation]['filters']
                predicates = operations[operation]['predicates']

                # iterate through the nested filters
                for a_filter in filters:
                    # iterate though values of a nested filter
                    for filter_key, filter_value in a_filter.items():
                        # choose filter array for query building
                        filter_array, queryBuilder = None, None
                        is_nested_query = False
                        neo4j_var = ''

                        # transform relay id into handle_id
                        old_filter_key = filter_key

                        try:
                            if filter_key.index('id') == 0:
                                # change value
                                try: # list value
                                    nfilter_value = []
                                    for fval in filter_value:
                                        handle_id_fval = relay.Node.from_global_id(fval)[1]
                                        handle_id_fval = int(handle_id_fval)
                                        nfilter_value.append(handle_id_fval)

                                    filter_value = nfilter_value
                                except: # single value
                                    filter_value = relay.Node.from_global_id(filter_value)[1]
                                    filter_value = int(filter_value)
                        except ValueError:
                            pass


                        if isinstance(filter_value, int) or isinstance(filter_value, str):
                            filter_array = ScalarQueryBuilder.filter_array
                            queryBuilder = ScalarQueryBuilder
                        elif isinstance(filter_value, list) and not (\
                                isinstance(filter_value[0], str) or isinstance(filter_value[0], int))\
                                or issubclass(type(filter_value), graphene.InputObjectType):
                            # set of type
                            is_nested_query = True
                            of_type = None

                            if isinstance(filter_value, list):
                                of_type = filter_value[0]._of_type
                            else:
                                of_type = filter_value._of_type

                            filter_array = InputFieldQueryBuilder.filter_array
                            queryBuilder = InputFieldQueryBuilder
                            additional_clause = of_type.match_additional_clause

                            if additional_clause:
                                if additional_clause not in raw_additional_clause.keys():
                                    raw_clause = additional_clause

                                    # format var name and additional match
                                    if issubclass(of_type, NIObjectType):
                                        neo4j_var = '{}{}'.format(of_type.neo4j_var_name, idxdict['node_idx'])
                                        neo4j_vars[of_type] = neo4j_var
                                        additional_clause = additional_clause.format(
                                            'n:{}'.format(nodetype),
                                            'l{}'.format(idxdict['subrel_idx']),
                                            idxdict['node_idx']
                                        )
                                        idxdict['node_idx'] = idxdict['node_idx'] + 1
                                        idxdict['subrel_idx'] = idxdict['subrel_idx'] + 1
                                        match_additional_nodes.append(additional_clause)
                                    elif issubclass(of_type, NIRelationType):
                                        neo4j_var = '{}{}'.format(of_type.neo4j_var_name, idxdict['rel_idx'])
                                        additional_clause = additional_clause.format(
                                            'n:{}'.format(nodetype),
                                            idxdict['rel_idx'],
                                            'z{}'.format(idxdict['subnode_idx'])
                                        )
                                        idxdict['rel_idx'] = idxdict['rel_idx'] + 1
                                        idxdict['subnode_idx'] = idxdict['subnode_idx'] + 1
                                        match_additional_rels.append(additional_clause)

                                    raw_additional_clause[raw_clause] = neo4j_var
                                else:
                                    neo4j_var = raw_additional_clause[additional_clause]
                        else:
                            filter_array = ScalarQueryBuilder.filter_array
                            queryBuilder = ScalarQueryBuilder

                        filter_field = cls.filter_names[filter_key]
                        field  = filter_field['field']

                        # append field to list to avoid the aditional match
                        filtered_fields.append(field)

                        suffix = filter_field['suffix']
                        field_type = filter_field['field_type']


                        # iterate through the keys of the filter array and extracts
                        # the predicate building function
                        for fa_suffix, fa_value in filter_array.items():
                            # change id field into handle_id for neo4j db
                            try:
                                if field.index('id') == 0:
                                    field = field.replace('id', 'handle_id')
                            except ValueError:
                                pass

                            if fa_suffix != '':
                                fa_suffix = '_{}'.format(fa_suffix)

                            # get the predicate
                            if suffix == fa_suffix:
                                build_predicate_func = fa_value['qpredicate']

                                predicate = build_predicate_func(field, filter_value, field_type, neo4j_var=neo4j_var)

                                if predicate:
                                    predicates.append(predicate)
                                elif predicate == "" and is_nested_query:
                                    # if the predicate comes empty, remove
                                    # index increases and additional matches
                                    if issubclass(of_type, NIObjectType):
                                        idxdict['node_idx'] = idxdict['node_idx'] - 1
                                        idxdict['subrel_idx'] = idxdict['subrel_idx'] - 1
                                        del match_additional_nodes[-1]
                                    elif issubclass(of_type, NIRelationType):
                                        idxdict['rel_idx'] = idxdict['rel_idx'] - 1
                                        idxdict['subnode_idx'] = idxdict['subnode_idx'] - 1
                                        del match_additional_rels[-1]

                operations[operation]['predicates'] = predicates

        and_query = ' AND '.join(operations['AND']['predicates'])
        or_query = ' OR '.join(operations['OR']['predicates'])

        if and_query and or_query:
            build_query = '({}) AND ({})'.format(
                and_query,
                or_query
            )
        else:
            if and_query:
                build_query = and_query
            elif or_query:
                build_query = or_query

        if build_query != '':
            build_query = 'WHERE {}'.format(build_query)

        # remove redundant additional clauses
        match_additional_nodes = list(set(match_additional_nodes))
        match_additional_rels = list(set(match_additional_rels))

        # prepare match clause
        node_match_clause = "(n:{label})".format(label=nodetype)
        additional_match_str = ', '.join( match_additional_nodes + match_additional_rels)

        if additional_match_str:
            node_match_clause = '{}, {}'.format(node_match_clause, additional_match_str)

        # create order query
        if orderBy:
            emptyFilter = False if filter else True
            of_type = cls._order_field_match[orderBy]['input_field']

            additional_clause = ''

            if hasattr(of_type, 'match_additional_clause'):
                additional_clause = of_type.match_additional_clause

                m = re.match(r"([\w|\_]*)_(ASC|DESC)", orderBy)
                prop = m[1]
                order = m[2]

                order_field_present = False

                if prop in filtered_fields:
                    order_field_present = True

                if issubclass(of_type, NIObjectType):
                    if order_field_present:
                        idxdict['node_idx'] = idxdict['node_idx'] - 1
                        idxdict['subrel_idx'] = idxdict['subrel_idx'] - 1

                    neo4j_var = '{}{}'.format(of_type.neo4j_var_name, idxdict['node_idx'])
                    neo4j_vars[of_type] = neo4j_var
                    additional_clause = additional_clause.format(
                        'n:{}'.format(nodetype),
                        'l{}'.format(idxdict['subrel_idx']),
                        idxdict['node_idx']
                    )

                    optional_matches = 'OPTIONAL MATCH {}'.format(additional_clause)
                    order_query = 'ORDER BY {} {}'.format(
                        '{}.name'.format(neo4j_var),
                        cls._desc_suffix if cls._order_field_match[orderBy]['is_desc'] else cls._asc_suffix,
                    )
                elif issubclass(of_type, NIRelationType):
                    if order_field_present:
                        idxdict['rel_idx'] = idxdict['rel_idx'] - 1
                        idxdict['subnode_idx'] = idxdict['subnode_idx'] - 1

                    neo4j_var = '{}{}'.format(of_type.neo4j_var_name, idxdict['rel_idx'])
                    neo4j_vars[of_type] = neo4j_var
                    additional_clause = additional_clause.format(
                        'n:{}'.format(nodetype),
                        idxdict['rel_idx'],
                        'z{}'.format(idxdict['subnode_idx'])
                    )

                    optional_matches = 'OPTIONAL MATCH {}'.format(additional_clause)
                    order_query = 'ORDER BY {} {}'.format(
                        '{}.name'.format(neo4j_var),
                        cls._desc_suffix if cls._order_field_match[orderBy]['is_desc'] else cls._asc_suffix,
                    )

                if order_field_present:
                    optional_matches = ''

            else:
                m = re.match(r"([\w|\_]*)_(ASC|DESC)", orderBy)
                prop = m[1]
                order = m[2]

                order_query = "ORDER BY n.{} {}".format(prop, order)

        if handle_id_order:
            order_nibble = 'ASC' if revert_order else 'DESC'
            order_query = "ORDER BY n.handle_id {}".format(order_nibble)

        # create filter query; this will filter out nodes that the user is
        # not allowed to see
        readable_ids = [ str(x) for x in readable_ids ] # string conversion
        ids = ', '.join(readable_ids)
        filter_prefix = 'AND' if build_query else 'WHERE'
        filter_query = '{prefix} n.handle_id in [{ids}]'.format(prefix=filter_prefix, ids=ids)

        q = """
            MATCH {node_match_clause}
            {optional_matches}
            {build_query}
            {filter_query}
            RETURN n
            {order_query}
            """.format(node_match_clause=node_match_clause,
                        optional_matches=optional_matches,
                        build_query=build_query, filter_query=filter_query,
                        order_query=order_query)

        logger.debug('Neo4j connection filter query:\n{}\n'.format(q))

        return q

    @classproperty
    def match_additional_clause(cls):
        return "({})-[{}]-({}{}:{})".format('{}', '{}', cls.neo4j_var_name, '{}',
                                        cls.NIMetaType.ni_type)

    neo4j_var_name = "m"

    class Meta:
        model = NodeHandle

########## END RELATION AND NODE TYPES


########## RELATION FIELD
class NIRelationField(NIBasicField):
    '''
    This field can be used in NIObjectTypes to represent a set relationships
    '''
    def __init__(self, field_type=graphene.List, manual_resolver=False,
                    type_args=(NIRelationType,), rel_name=None, **kwargs):
        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_args       = type_args
        self.rel_name        = rel_name

    def get_resolver(self, **kwargs):
        # getting nimodel
        nimodel = nc.models.BaseRelationshipModel

        if self.type_args != (NIRelationType,):
            rel_type = self.type_args[0]
            nimeta = getattr(rel_type, 'NIMetaType', None)
            if nimeta:
                nimodel = getattr(nimeta, 'nimodel', None)

        field_name = kwargs.get('field_name')
        rel_name   = kwargs.get('rel_name')

        if not field_name:
            raise Exception(
                'Field name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )
        def resolve_node_relation(self, info, **kwargs):
            ret = []
            reldicts = self.get_node().relationships.get(rel_name, None)

            if reldicts:
                for reldict in reldicts:
                    relbundle = nc.get_relationship_bundle(nc.graphdb.manager, relationship_id=reldict['relationship_id'])
                    relation = nimodel(nc.graphdb.manager)
                    relation.load(relbundle)
                    ret.append(relation)

            return ret

        return resolve_node_relation
########## END RELATION FIELD

########## MUTATION FACTORY
class NodeHandler(NIObjectType):
    name = NIStringField(type_kwargs={ 'required': True })


class DeleteRelationship(relay.ClientIDMutation):
    class Input:
        relation_id = graphene.Int(required=True)

    success = graphene.Boolean(required=True)
    relation_id = graphene.Int(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        relation_id = input.get("relation_id", None)
        success = False

        try:
            relationship = nc.get_relationship_model(nc.graphdb.manager, relation_id)

            # check permissions before delete
            start_id = relationship.start['handle_id']
            end_id = relationship.end['handle_id']

            authorized_start = sriutils.authorice_read_resource(
                info.context.user, start_id
            )

            authorized_end = sriutils.authorice_read_resource(
                info.context.user, end_id
            )

            if authorized_start and authorized_end:
                activitylog.delete_relationship(info.context.user, relationship)
                relationship.delete()

            success = True
        except nc.exceptions.RelationshipNotFound:
            success = True

        return DeleteRelationship(success=success, relation_id=relation_id)


class AbstractNIMutation(relay.ClientIDMutation):
    errors = graphene.List(ErrorType)

    @classmethod
    def __init_subclass_with_meta__(
        cls, output=None, input_fields=None, arguments=None, name=None, **options
    ):
        ''' In this method we'll build an input nested object using the form
        '''
        # read form
        ni_metaclass  = getattr(cls, 'NIMetaClass')
        graphql_type  = getattr(ni_metaclass, 'graphql_type', None)
        django_form   = getattr(ni_metaclass, 'django_form', None)
        mutation_name = getattr(ni_metaclass, 'mutation_name', None)
        is_create     = getattr(ni_metaclass, 'is_create', False)
        is_delete     = getattr(ni_metaclass, 'is_delete', False)
        include       = getattr(ni_metaclass, 'include', None)
        exclude       = getattr(ni_metaclass, 'exclude', None)

        if include and exclude:
            raise Exception('Only "include" or "exclude" metafields can be defined')

        # build fields into Input
        inner_fields = {}
        if django_form:
            for class_field_name, class_field in django_form.__dict__.items():
                if class_field_name == 'declared_fields' or class_field_name == 'base_fields':
                    for field_name, field in class_field.items():
                        # convert form field into mutation input field
                        graphene_field = cls.form_to_graphene_field(field)

                        if graphene_field:
                            add_field = False

                            if hasattr(django_form, 'Meta') and hasattr(django_form.Meta, 'exclude'):
                                if field not in django_form.Meta.exclude:
                                    add_field = True
                            else:
                                add_field = True

                            if include:
                                if field_name not in include:
                                    add_field = False
                            elif exclude:
                                if field_name in exclude:
                                    add_field = False

                            if add_field:
                                inner_fields[field_name] = graphene_field

        # add handle_id
        if not is_create:
            inner_fields['id'] = graphene.ID(required=True)

        # add Input attribute to class
        inner_class = type('Input', (object,), inner_fields)
        setattr(cls, 'Input', inner_class)

        # add Input to private attribute
        if graphql_type:
            op_name = 'Create' if is_create else 'Update'
            op_name = 'Delete' if is_delete else op_name
            type_name = graphql_type.__name__
            inner_input = type('Single{}Input'.format(op_name + type_name),
                (graphene.InputObjectType, ), inner_fields)

            setattr(ni_metaclass, '_input_list', graphene.List(inner_input))
            setattr(ni_metaclass, '_payload_list', graphene.List(cls))

        # add the converted fields to the metaclass so we can get them later
        setattr(ni_metaclass, 'inner_fields', inner_fields)
        setattr(cls, 'NIMetaClass', ni_metaclass)

        cls.add_return_type(graphql_type)

        super(AbstractNIMutation, cls).__init_subclass_with_meta__(
            output, inner_fields, arguments, name=mutation_name, **options
        )

    @classmethod
    def get_returntype_name(cls, graphql_type):
        graphql_typename = graphql_type.__name__
        fmt_name = graphql_typename[0].lower() + graphql_typename[1:]

        return fmt_name

    @classmethod
    def add_return_type(cls, graphql_type):
        if graphql_type:
            payload_name = cls.get_returntype_name(graphql_type)

            setattr(cls, payload_name, graphene.Field(graphql_type))

    @classmethod
    def form_to_graphene_field(cls, form_field, include=None, exclude=None):
        '''Django form to graphene field conversor
        '''
        graphene_field = None

        # get attributes
        graph_kwargs = {}
        disabled = False
        for attr_name, attr_value in form_field.__dict__.items():
            if attr_name == 'required':
                graph_kwargs['required'] = attr_value
            elif attr_name == 'disabled':
                disabled = attr_value
            elif attr_name == 'initial':
                graph_kwargs['default_value'] = attr_value

        # compare types
        if not disabled:
            if isinstance(form_field, forms.BooleanField):
                graphene_field = graphene.Boolean(**graph_kwargs)
            elif isinstance(form_field, forms.CharField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.ChoiceField):
                graphene_field = ChoiceScalar(**graph_kwargs)
            elif isinstance(form_field, forms.FloatField):
                graphene_field = graphene.Float(**graph_kwargs)
            elif isinstance(form_field, forms.IntegerField):
                graphene_field = graphene.Int(**graph_kwargs)
            elif isinstance(form_field, forms.MultipleChoiceField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.URLField):
                graphene_field = graphene.String(**graph_kwargs)
            else:
                graphene_field = graphene.String(**graph_kwargs)

            if isinstance(form_field, forms.NullBooleanField):
                graphene_field = NullBoolean(**graph_kwargs)

            ### fields to be implement: ###
            # IPAddrField (CharField)
            # JSONField (CharField)
            # NodeChoiceField (ModelChoiceField)
            # DatePickerField (DateField)
            # description_field (CharField)
            # relationship_field (ChoiceField / IntegerField)
        else:
            return None

        return graphene_field

    @classmethod
    def get_type(cls):
        ni_metaclass = getattr(cls, 'NIMetaClass')
        return getattr(ni_metaclass, 'typeclass')

    @classmethod
    def from_input_to_request(cls, user, **input):
        '''
        Gets the input data from the input inner class, and this is build using
        the fields in the django form. It returns a nodehandle of the type
        defined by the NIMetaClass
        '''
        # get ni metaclass data
        ni_metaclass   = getattr(cls, 'NIMetaClass')
        form_class     = getattr(ni_metaclass, 'django_form', None)
        request_path   = getattr(ni_metaclass, 'request_path', '/')
        is_create      = getattr(ni_metaclass, 'is_create', False)
        inner_fields   = getattr(ni_metaclass, 'inner_fields', [])

        graphql_type   = getattr(ni_metaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype')

        # get input values
        noninput_fields = list(inner_fields.keys())
        input_class = getattr(cls, 'Input', None)
        input_params = {}
        if input_class:
            for attr_name, attr_field in input_class.__dict__.items():
                attr_value = input.get(attr_name)

                if attr_value != None:
                    input_params[attr_name] = attr_value
                    if attr_name in noninput_fields:
                        noninput_fields.remove(attr_name)

        # if it's an edit mutation add handle_id
        # and also add the existent values in the request
        if not is_create:
            input_params['id'] = input.get('id')
            handle_id = None
            handle_id = relay.Node.from_global_id(input_params['id'])[1]

            # get previous instance
            nh = NodeHandle.objects.get(handle_id=handle_id)
            node = nh.get_node()
            for noninput_field in noninput_fields:
                if noninput_field in node.data:
                    input_params[noninput_field] = node.data.get(noninput_field)

        # morph ids for relation processors
        relations_processors = getattr(ni_metaclass, 'relations_processors', None)

        if relations_processors:
            for relation_name in relations_processors.keys():
                relay_id = input.get(relation_name, None)

                if relay_id:
                    handle_id = relay.Node.from_global_id(relay_id)[1]
                    input_params[relation_name] = handle_id

        # forge request
        request_factory = RequestFactory()
        request = request_factory.post(request_path, data=input_params)
        request.user = user

        return (request, dict(form_class=form_class, node_type=node_type,
                                node_meta_type=node_meta_type))

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context or not info.context.user.is_authenticated:
            raise GraphQLAuthException()

        # convert the input to a request object for the form to processs
        reqinput = cls.from_input_to_request(info.context.user, **input)

        # get input context, otherwise get the type context
        graphql_type = cls.get_graphql_type()
        input_context = input.get('context', graphql_type.get_type_context())
        # add it to the dict
        reqinput[1]['input_context'] = input_context

        # call subclass do_request method
        has_error, ret = cls.do_request(reqinput[0], **reqinput[1])

        init_params = {}

        if not has_error:
            for key, value in ret.items():
                init_params[key] = value
        else:
            init_params['errors'] = ret

        return cls(**init_params)

    @classmethod
    def get_graphql_type(cls):
        ni_metaclass  = getattr(cls, 'NIMetaClass')
        graphql_type  = getattr(ni_metaclass, 'graphql_type', None)

        return graphql_type

    @classmethod
    def format_error_array(cls, errordict):
        errors = []

        for key, value in errordict.items():
            errors.append(ErrorType(field=key, messages=[value.as_data()[0].messages[0]]))

        return errors

    @classmethod
    def process_relations(cls, request, form, nodehandler):
        nimetaclass = getattr(cls, 'NIMetaClass')
        relations_processors = getattr(nimetaclass, 'relations_processors', None)

        if relations_processors:
            for relation_name, relation_f in relations_processors.items():
                relation_f(request, form, nodehandler, relation_name)

    @classmethod
    def process_subentities(cls, request, form, master_nh, context):
        nimetaclass = getattr(cls, 'NIMetaClass')
        subentity_processors = getattr(nimetaclass, 'subentity_processors', None)

        if subentity_processors:
            for sub_name, sub_props in subentity_processors.items():
                type_slug = sub_props['type_slug']
                fields = sub_props['fields']
                meta_type = sub_props['meta_type']
                link_method = sub_props['link_method']

                node_type = NodeType.objects.get(slug=type_slug)

                # forge attributes object
                input_params = {}
                sub_handle_id = None
                node_name = None

                for fform_name, fform_value in fields.items():
                    if fform_name == 'id':
                        sub_id = form.cleaned_data.get(fform_value, None)
                        if sub_id:
                            _type, sub_handle_id = relay.Node.from_global_id(sub_id)
                    else:
                        if fform_name == 'name':
                            node_name = form.cleaned_data.get(fform_value, None)

                        input_params[fform_name] = form.cleaned_data.get(fform_value, None)

                nh = None

                # create or edit entity
                if node_name:
                    if not sub_handle_id: # create
                        nh = NodeHandle(
                            node_name=node_name,
                            node_type=node_type,
                            node_meta_type=meta_type,
                            creator=request.user,
                            modifier=request.user,
                        )
                        nh.save()
                    else: # edit
                        nh = NodeHandle.objects.get(handle_id=sub_handle_id)

                    # add neo4j attributes
                    for key, value in input_params.items():
                        nh.get_node().remove_property(key)
                        nh.get_node().add_property(key, value)

                    # add relation to master node
                    link_method = getattr(master_nh, link_method, None)

                    if link_method:
                        link_method(nh.handle_id)

                    # add to permission context
                    NodeHandleContext(nodehandle=nh, context=context).save()

    class Meta:
        abstract = True

'''
This classes are used by the Mutation factory but it could be used as the
superclass of a manualy coded class in case it's needed.
'''

class CreateNIMutation(AbstractNIMutation):
    '''
    Implements a creation mutation for a specific NodeType
    '''
    class NIMetaClass:
        request_path   = None
        is_create      = True
        graphql_type   = None
        include        = None
        exclude        = None

    @classmethod
    def get_form_to_nodehandle_func(cls):
        return helpers.form_to_generic_node_handle

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class = kwargs.get('form_class')
        context    = kwargs.get('input_context')

        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        property_update = getattr(nimetaclass, 'property_update', None)
        relay_extra_ids = getattr(nimetaclass, 'relay_extra_ids', None)

        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = slugify(getattr(nimetatype, 'ni_type'))
        node_meta_type = getattr(nimetatype, 'ni_metatype')

        has_error      = False

        # check it can write on this context
        authorized = sriutils.authorize_create_resource(request.user, context)

        if not authorized:
            raise GraphQLAuthException()

        ## code from role creation
        post_data = request.POST.copy()

        # convert relay ids to django ids
        if relay_extra_ids:
            for extra_id in relay_extra_ids:
                rela_id_val = post_data.get(extra_id)
                if rela_id_val:
                    rela_id_val = relay.Node.from_global_id(rela_id_val)[1]
                    post_data.pop(extra_id)
                    post_data.update({ extra_id: rela_id_val})

        form = form_class(post_data)
        if form.is_valid():
            try:
                form_to_nodehandle = cls.get_form_to_nodehandle_func()
                nh = form_to_nodehandle(request, form,
                        node_type, node_meta_type)
            except UniqueNodeError:
                has_error = True
                return has_error, [ErrorType(field="_", messages=["A {} with that name already exists.".format(node_type)])]

            helpers.form_update_node(request.user, nh.handle_id, form, property_update)

            # add default context
            NodeHandleContext(nodehandle=nh, context=context).save()

            # process relations if implemented
            if not has_error:
                nh_reload, nodehandler = helpers.get_nh_node(nh.handle_id)
                cls.process_relations(request, form, nodehandler)

            # process subentities if implemented
            if not has_error:
                nh_reload, nodehandler = helpers.get_nh_node(nh.handle_id)
                cls.process_subentities(request, form, nodehandler, context)

            return has_error, { cls.get_returntype_name(graphql_type): nh }
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict


class CreateUniqueNIMutation(CreateNIMutation):
    '''
    Implements a creation mutation for a specific NodeType, the difference
    between this and CreateNIMutation is that this mutation create unique nodes
    '''

    @classmethod
    def get_form_to_nodehandle_func(cls):
        return helpers.form_to_unique_node_handle


class UpdateNIMutation(AbstractNIMutation):
    '''
    Implements an update mutation for a specific NodeType
    '''
    class NIMetaClass:
        request_path   = None
        graphql_type   = None
        include        = None
        exclude        = None

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class      = kwargs.get('form_class')
        context    = kwargs.get('input_context')

        nimetaclass     = getattr(cls, 'NIMetaClass')
        graphql_type    = getattr(nimetaclass, 'graphql_type')
        property_update = getattr(nimetaclass, 'property_update', None)
        relay_extra_ids = getattr(nimetaclass, 'relay_extra_ids', None)

        nimetatype      = getattr(graphql_type, 'NIMetaType')
        node_type       = slugify(getattr(nimetatype, 'ni_type'))
        node_meta_type  = getattr(nimetatype, 'ni_metatype')
        context_method  = getattr(nimetatype, 'context_method')
        id              = request.POST.get('id')
        has_error       = False

        # check authorization
        handle_id = relay.Node.from_global_id(id)[1]
        authorized = sriutils.authorice_write_resource(request.user, handle_id)

        if not authorized:
            raise GraphQLAuthException()

        nh, nodehandler = helpers.get_nh_node(handle_id)
        if request.POST:
            post_data = request.POST.copy()

            # convert relay ids to django ids
            if relay_extra_ids:
                for extra_id in relay_extra_ids:
                    rela_id_val = post_data.get(extra_id)
                    if rela_id_val:
                        rela_id_val = relay.Node.from_global_id(rela_id_val)[1]
                        post_data.pop(extra_id)
                        post_data.update({ extra_id: rela_id_val})

            form = form_class(post_data)
            if form.is_valid():
                # Generic node update
                helpers.form_update_node(request.user, nodehandler.handle_id, form, property_update)

                # process relations if implemented
                cls.process_relations(request, form, nodehandler)

                # process subentities if implemented
                cls.process_subentities(request, form, nodehandler, context)

                return has_error, { cls.get_returntype_name(graphql_type): nh }
            else:
                has_error = True
                errordict = cls.format_error_array(form.errors)
                return has_error, errordict
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict


class DeleteNIMutation(AbstractNIMutation):
    '''
    Implements an delete mutation for a specific NodeType
    '''
    class NIMetaClass:
        request_path   = None
        graphql_type   = None
        is_delete      = False

    @classmethod
    def add_return_type(cls, graphql_type):
        setattr(cls, 'success', graphene.Boolean(required=True))

    @classmethod
    def do_request(cls, request, **kwargs):
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

        # check authorization
        authorized = sriutils.authorice_write_resource(request.user, handle_id)

        if not authorized:
            raise GraphQLAuthException()

        nh, node = helpers.get_nh_node(handle_id)

        # delete associated nodes
        cls.delete_nodes(nh, request.user)

        # delete node
        success = helpers.delete_node(request.user, node.handle_id)

        return not success, {'success': success}

    @classmethod
    def delete_nodes(cls, nodehandler, user):
        nimetaclass = getattr(cls, 'NIMetaClass')
        delete_nodes = getattr(nimetaclass, 'delete_nodes', None)

        if delete_nodes:
            for relation_name, relation_f in delete_nodes.items():
                relation_f(nodehandler, relation_name, user)

class MultipleMutation(relay.ClientIDMutation):
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if not info.context or not info.context.user.is_authenticated:
            raise GraphQLAuthException()

        # get input values
        create_inputs = input.get("create_inputs")
        update_inputs = input.get("update_inputs")
        delete_inputs = input.get("delete_inputs")
        detach_inputs = input.get("detach_inputs")

        # get underlying mutations
        nimetaclass = getattr(cls, 'NIMetaClass')
        create_mutation = getattr(nimetaclass, 'create_mutation', None)
        update_mutation = getattr(nimetaclass, 'update_mutation', None)
        delete_mutation = getattr(nimetaclass, 'delete_mutation', None)
        detach_mutation = getattr(nimetaclass, 'detach_mutation', None)

        ret_created = []
        if create_inputs:
            for input in create_inputs:
                ret = create_mutation.mutate_and_get_payload(root, info, **input)
                ret_created.append(ret)

        ret_updated = []
        if update_inputs:
            for input in update_inputs:
                ret = update_mutation.mutate_and_get_payload(root, info, **input)
                ret_updated.append(ret)

        ret_deleted = []
        if delete_inputs:
            for input in delete_inputs:
                ret = delete_mutation.mutate_and_get_payload(root, info, **input)
                ret_deleted.append(ret)

        ret_detached = []
        if detach_inputs:
            for input in detach_inputs:
                ret = detach_mutation.mutate_and_get_payload(root, info, **input)
                ret_deleted.append(ret)

        return cls(
            created=ret_created, updated=ret_updated,
            deleted=ret_deleted, detached=ret_detached
        )


class CompositeMutation(relay.ClientIDMutation):
    class Input:
        pass

    @classmethod
    def __init_subclass_with_meta__(
        cls, **options
    ):
        '''
        In this method we'll build the default inputs for a composite mutation
        '''
        # get types and mutation factories
        ni_metaclass = getattr(cls, 'NIMetaClass')
        graphql_type = getattr(ni_metaclass, 'graphql_type', None)
        graphql_subtype = getattr(ni_metaclass, 'graphql_subtype', None)
        main_mutation_f = getattr(ni_metaclass, 'main_mutation_f', None)
        secondary_mutation_f = getattr(ni_metaclass, 'secondary_mutation_f', None)
        include_metafields = getattr(ni_metaclass, 'include_metafields', None)
        exclude_metafields = getattr(ni_metaclass, 'exclude_metafields', None)

        # get mandatory input
        cls_input = getattr(cls, 'Input')

        if not cls_input:
            raise Exception('{} should define an Input class (it can be empty)')

        # if both are set
        if exclude_metafields and include_metafields:
            raise Exception("Only exclude_metafields or include_metafields can"\
                            " be defined on {} NIMetaClass".format(cls))

        # add main mutation fields if present
        if main_mutation_f:
            # add metaclass attributes
            ni_metaclass.create_mutation = main_mutation_f.get_create_mutation()
            ni_metaclass.update_mutation = main_mutation_f.get_update_mutation()

            # add payload attributes
            cls.created = graphene.Field(main_mutation_f.get_create_mutation())
            cls.updated = graphene.Field(main_mutation_f.get_update_mutation())

            # add regular inputs
            cls_input.create_input = graphene.Field(main_mutation_f.get_create_mutation().Input)
            cls_input.update_input = graphene.Field(main_mutation_f.get_update_mutation().Input)

        if secondary_mutation_f:
            # add metaclass attributes
            ni_metaclass.create_submutation = secondary_mutation_f.get_create_mutation()
            ni_metaclass.update_submutation = secondary_mutation_f.get_update_mutation()
            ni_metaclass.delete_submutation = secondary_mutation_f.get_delete_mutation()

            # add payload attributes
            cls.subcreated = graphene.List(secondary_mutation_f.get_create_mutation())
            cls.subupdated = graphene.List(secondary_mutation_f.get_update_mutation())
            cls.subdeleted = graphene.List(secondary_mutation_f.get_delete_mutation())

            # add regular inputs
            cls_input.create_subinputs = graphene.List(secondary_mutation_f.get_create_mutation().Input)
            cls_input.update_subinputs = graphene.List(secondary_mutation_f.get_update_mutation().Input)
            cls_input.delete_subinputs = graphene.List(secondary_mutation_f.get_delete_mutation().Input)

        # add unlink_submutation to metaclass, payload and input
        # as these are present on every composite mutation
        ni_metaclass.unlink_submutation = DeleteRelationship
        cls.unlinked = graphene.List(DeleteRelationship)
        cls_input.unlink_subinputs = graphene.List(DeleteRelationship.Input)

        # add metatype input fields
        metatype_interface = graphql_type.get_metatype_interface()
        avoid_fields = ('__module__', '__doc__', '_meta', 'name', 'with_same_name')

        cls.metafields_payload = {}
        cls.metafields_input = {}
        cls.metafields_classes = {}

        if metatype_interface:
            # go over attributes that aren't in the avoid list
            # or in the include and exclude params
            for metafield_name, metafield in metatype_interface.__dict__.items():
                if metafield_name in avoid_fields:
                    continue

                if include_metafields and metafield_name not in include_metafields:
                    continue

                if exclude_metafields and metafield_name in exclude_metafields:
                    continue

                # add field class array
                cls.metafields_classes[metafield_name] = []

                metafield_interface = None
                is_list = False

                if isinstance(metafield, graphene.types.field.Field):
                    metafield_interface = metafield._type
                elif isinstance(metafield, graphene.types.structures.List):
                    metafield_interface = metafield._of_type
                    is_list = True

                # we'll try to resolve the lambda if that's the case
                try:
                    metafield_interface = metafield_interface()
                except:
                    pass

                # process skip NINode
                if metafield_interface == NINode:
                    continue

                # get all types that implement metafield_interface
                # we need to add a mutation for each one
                subclass_list = subclasses_interfaces[metafield_interface]

                for a_subclass in subclass_list:
                    # add class to dict with
                    cls.metafields_classes[metafield_name].append(a_subclass)

                    # init internal attribute storage
                    cls.metafields_payload[a_subclass] = {
                        'created': { 'name': None },
                        'updated': { 'name': None },
                        'deleted': { 'name': None },
                        'is_list': is_list,
                    }

                    cls.metafields_input[a_subclass] = {
                        'create': { 'name': None },
                        'update': { 'name': None },
                        'delete': { 'name': None },
                        'is_list': is_list,
                    }

                    # get mutations for each attribute
                    create_mutation = a_subclass.get_create_mutation()
                    update_mutation = a_subclass.get_update_mutation()
                    delete_mutation = a_subclass.get_delete_mutation()

                    # payload names
                    name_prefix = '{}_{}'.format(
                        metafield_name, a_subclass.__name__.lower())
                    created_name = '{}_created'.format(name_prefix)
                    updated_name = '{}_updated'.format(name_prefix)
                    deleted_name = '{}_deleted'.format(name_prefix)

                    # get inputs for each input attribute
                    # input names
                    create_name = 'create_{}'.format(name_prefix)
                    update_name = 'update_{}'.format(name_prefix)
                    delete_name = 'deleted_{}'.format(name_prefix)

                    if create_mutation:
                        # add to payload
                        payload_field = graphene.Field(create_mutation)
                        if is_list:
                            payload_field = graphene.List(create_mutation)

                        setattr(cls, created_name, payload_field)
                        cls.metafields_payload[a_subclass]['created']['name']\
                            = created_name

                        # add to input
                        input_field = graphene.Field(create_mutation.Input)
                        if is_list:
                            input_field = graphene.List(create_mutation.Input)

                        setattr(cls_input, create_name, input_field)
                        cls.metafields_input[a_subclass]['create']['name']\
                            = create_name

                    if update_mutation:
                        # add to payload
                        payload_field = graphene.Field(update_mutation)
                        if is_list:
                            payload_field = graphene.List(update_mutation)

                        setattr(cls, updated_name, payload_field)
                        cls.metafields_payload[a_subclass]['updated']['name']\
                            = updated_name

                        # add to input
                        input_field = graphene.Field(update_mutation.Input)
                        if is_list:
                            input_field = graphene.List(update_mutation.Input)

                        setattr(cls_input, update_name, input_field)
                        cls.metafields_input[a_subclass]['update']['name']\
                            = update_name

                    if delete_mutation:
                        # add to payload
                        payload_field = graphene.Field(delete_mutation)
                        if is_list:
                            payload_field = graphene.List(delete_mutation)

                        setattr(cls, deleted_name, payload_field)
                        cls.metafields_payload[a_subclass]['deleted']['name']\
                            = deleted_name

                        # add to input
                        input_field = graphene.Field(delete_mutation.Input)
                        if is_list:
                            input_field = graphene.List(delete_mutation.Input)

                        setattr(cls_input, delete_name, input_field)
                        cls.metafields_input[a_subclass]['delete']['name']\
                            = delete_name

            setattr(cls, 'Input', cls_input)

        super(CompositeMutation, cls).__init_subclass_with_meta__(
            **options
        )

    @classmethod
    def get_link_kwargs(cls, master_input, slave_input):
        return {}

    @classmethod
    def link_slave_to_master(cls, user, master_nh, slave_nh, **kwargs):
        pass

    @classmethod
    def forge_payload(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    def process_extra_subentities(cls, user, master_nh, root, info, input, context):
        pass

    @classmethod
    def process_metatype_subentities(cls, user, master_nh, root, info, input, context):
        master_ret = dict()

        for metafield_name, subclass_list in cls.metafields_classes.items():
            for a_subclass in subclass_list:
                created_ifield = cls.metafields_input[a_subclass]['create']['name']
                updated_ifield = cls.metafields_input[a_subclass]['update']['name']
                deleted_ifield = cls.metafields_input[a_subclass]['delete']['name']

                is_list = cls.metafields_payload[a_subclass]['is_list']

                create_subinputs = None
                update_subinputs = None
                delete_subinputs = None

                if created_ifield:
                    create_subinputs = input.get(created_ifield)

                if updated_ifield:
                    update_subinputs = input.get(updated_ifield)

                if deleted_ifield:
                    delete_subinputs = input.get(deleted_ifield)

                create_submutation = a_subclass.get_create_mutation()
                update_submutation = a_subclass.get_update_mutation()
                delete_submutation = a_subclass.get_delete_mutation()
                extract_param = AbstractNIMutation.get_returntype_name(a_subclass)

                ret_subcreated = None
                ret_subupdated = None
                ret_subdeleted = None

                link_method_name = 'link_{}'.format(metafield_name)
                link_method = getattr(a_subclass, link_method_name, None)

                # process create
                if create_subinputs:
                    ret_subcreated = []

                    if is_list:
                        for subinput in create_subinputs:
                            subinput['context'] = context
                            ret = create_submutation\
                                .mutate_and_get_payload(root, info, **subinput)
                            ret_subcreated.append(ret)

                            # link if it's possible
                            sub_errors = getattr(ret, 'errors', None)
                            sub_created = getattr(ret, extract_param, None)

                            if not sub_errors and sub_created and link_method:
                                link_method(user, master_nh, sub_created)
                    else:
                        subinput = create_subinputs
                        subinput['context'] = context
                        ret = create_submutation\
                            .mutate_and_get_payload(root, info, **subinput)

                        # link if it's possible
                        sub_errors = getattr(ret, 'errors', None)
                        sub_created = getattr(ret, extract_param, None)

                        if not sub_errors and sub_created and link_method:
                            link_method(user, master_nh, sub_created)

                        ret_subcreated = ret

                # process update
                if update_subinputs:
                    ret_subupdated = []

                    if is_list:
                        for subinput in update_subinputs:
                            subinput['context'] = context
                            ret = update_submutation\
                                .mutate_and_get_payload(root, info, **subinput)
                            ret_subupdated.append(ret)

                            # link if it's possible
                            sub_errors = getattr(ret, 'errors', None)
                            sub_edited = getattr(ret, extract_param, None)

                            if not sub_errors and sub_edited and link_method:
                                link_method(user, master_nh, sub_edited)
                    else:
                        subinput = update_subinputs
                        subinput['context'] = context
                        ret = update_submutation\
                            .mutate_and_get_payload(root, info, **subinput)

                        # link if it's possible
                        sub_errors = getattr(ret, 'errors', None)
                        sub_edited = getattr(ret, extract_param, None)

                        if not sub_errors and sub_edited and link_method:
                            link_method(user, master_nh, sub_edited)

                        ret_subcreated = ret

                # process delete
                if delete_subinputs:
                    ret_subdeleted = []

                    if is_list:
                        for subinput in delete_subinputs:
                            ret = delete_submutation\
                                .mutate_and_get_payload(root, info, **subinput)
                            ret_subdeleted.append(ret)
                    else:
                        ret_subdeleted = delete_submutation\
                            .mutate_and_get_payload(root, info, **delete_subinputs)

                # add the payload results
                create_payload = cls.metafields_payload[a_subclass]['created']['name']
                update_payload = cls.metafields_payload[a_subclass]['updated']['name']
                delete_payload = cls.metafields_payload[a_subclass]['deleted']['name']

                if create_payload:
                    master_ret[create_payload] = ret_subcreated

                if update_payload:
                    master_ret[update_payload] = ret_subupdated

                if delete_payload:
                    master_ret[delete_payload] = ret_subdeleted

        return master_ret

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        # check if the user is authenticated
        if not info.context or not info.context.user.is_authenticated:
            raise GraphQLAuthException()

        # get main entity possible inputs
        user = info.context.user
        create_input = input.get("create_input")
        update_input = input.get("update_input")

        nimetaclass = getattr(cls, 'NIMetaClass')
        graphql_type = getattr(nimetaclass, 'graphql_type', None)
        graphql_subtype = getattr(nimetaclass, 'graphql_subtype', None)
        create_mutation = getattr(nimetaclass, 'create_mutation', None)
        update_mutation = getattr(nimetaclass, 'update_mutation', None)
        context         = getattr(nimetaclass, 'context', None)

        # this handle_id will be set to the created or updated main entity
        main_handle_id = None
        ret_created = None
        ret_updated = None

        ret_subcreated = None
        ret_subupdated = None
        ret_subdeleted = None
        ret_unlinked = None

        has_main_errors = False

        # perform main operation
        create = False

        if create_input:
            create = True
            create_input['context'] = context
            ret_created = create_mutation.mutate_and_get_payload(root, info, **create_input)
        elif update_input:
            update_input['context'] = context
            ret_updated = update_mutation.mutate_and_get_payload(root, info, **update_input)
        else:
            raise Exception('At least an input should be provided')

        main_ret = ret_created if create else ret_updated
        main_input = create_input if create else update_input

        # extract handle_id from the returned payload
        extract_param = AbstractNIMutation.get_returntype_name(graphql_type)
        main_nh = getattr(main_ret, extract_param, None)
        main_handle_id = None

        if main_nh:
            main_handle_id = main_nh.handle_id

        # check if there's errors in the form
        errors = getattr(main_ret, 'errors', None)

        # extra params for return
        ret_extra_subentities = {}
        ret_metatype_subentities = {}

        # if everything went fine, proceed with the subentity list
        if main_handle_id and not errors:
            create_subinputs = input.get("create_subinputs")
            update_subinputs = input.get("update_subinputs")
            delete_subinputs = input.get("delete_subinputs")
            unlink_subinputs = input.get("unlink_subinputs")

            create_submutation = getattr(nimetaclass, 'create_submutation', None)
            update_submutation = getattr(nimetaclass, 'update_submutation', None)
            delete_submutation = getattr(nimetaclass, 'delete_submutation', None)
            unlink_submutation = getattr(nimetaclass, 'unlink_submutation', None)

            extract_param = AbstractNIMutation.get_returntype_name(graphql_subtype)

            if create_subinputs:
                ret_subcreated = []

                for subinput in create_subinputs:
                    subinput['context'] = context
                    ret = create_submutation.mutate_and_get_payload(root, info, **subinput)
                    ret_subcreated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_created = getattr(ret, extract_param, None)

                    if not sub_errors and sub_created:
                        link_kwargs = cls.get_link_kwargs(main_input, subinput)
                        cls.link_slave_to_master(user, main_nh, sub_created, **link_kwargs)

            if update_subinputs:
                ret_subupdated = []

                for subinput in update_subinputs:
                    subinput['context'] = context
                    ret = update_submutation.mutate_and_get_payload(root, info, **subinput)
                    ret_subupdated.append(ret)

                    # link if it's possible
                    sub_errors = getattr(ret, 'errors', None)
                    sub_edited = getattr(ret, extract_param, None)

                    if not sub_errors and sub_edited:
                        link_kwargs = cls.get_link_kwargs(main_input, subinput)
                        cls.link_slave_to_master(user, main_nh, sub_edited, **link_kwargs)

            if delete_subinputs:
                ret_subdeleted = []

                for subinput in delete_subinputs:
                    ret = delete_submutation.mutate_and_get_payload(root, info, **subinput)
                    ret_subdeleted.append(ret)

            if unlink_subinputs:
                ret_unlinked = []

                for subinput in unlink_subinputs:
                    ret = unlink_submutation.mutate_and_get_payload(root, info, **subinput)
                    ret_unlinked.append(ret)

            ret_extra_subentities = \
                cls.process_extra_subentities(user, main_nh, root, info, input, context)

            ret_metatype_subentities = \
                cls.process_metatype_subentities(user, main_nh, root, info, input, context)

        payload_kwargs = dict(
            created=ret_created, updated=ret_updated,
            subcreated=ret_subcreated, subupdated=ret_subupdated,
            subdeleted=ret_subdeleted, unlinked=ret_unlinked
        )

        if ret_extra_subentities:
            payload_kwargs = {**payload_kwargs, **ret_extra_subentities}

        if ret_metatype_subentities:
            payload_kwargs = {**payload_kwargs, **ret_metatype_subentities}

        return cls.forge_payload(
            **payload_kwargs
        )


class NIMutationFactory():
    '''
    The mutation factory takes a django form, a node type and some parameters
    more and generates a mutation to create/update/delete nodes. If a higher
    degree of control is needed the classes CreateNIMutation, UpdateNIMutation
    and DeleteNIMutation could be subclassed to override any method's behaviour.
    '''

    node_type      = None
    node_meta_type = None
    request_path   = None

    create_mutation_class = CreateNIMutation
    update_mutation_class = UpdateNIMutation
    delete_mutation_class = DeleteNIMutation

    def __init_subclass__(cls, **kwargs):
        metaclass_name = 'NIMetaClass'
        nh_field = 'nodehandle'

        cls._create_mutation = None
        cls._update_mutation = None
        cls._delete_mutation = None

        # check defined form attributes
        ni_metaclass    = getattr(cls, metaclass_name)
        form            = getattr(ni_metaclass, 'form', None)
        create_form     = getattr(ni_metaclass, 'create_form', None)
        update_form     = getattr(ni_metaclass, 'update_form', None)
        request_path    = getattr(ni_metaclass, 'request_path', None)
        graphql_type    = getattr(ni_metaclass, 'graphql_type', NodeHandler)
        create_include  = getattr(ni_metaclass, 'create_include', None)
        create_exclude  = getattr(ni_metaclass, 'create_exclude', None)
        update_include  = getattr(ni_metaclass, 'update_include', None)
        update_exclude  = getattr(ni_metaclass, 'update_exclude', None)
        property_update = getattr(ni_metaclass, 'property_update', None)
        relay_extra_ids = getattr(ni_metaclass, 'relay_extra_ids', None)
        unique_node     = getattr(ni_metaclass, 'unique_node', False)

        manual_create   = getattr(ni_metaclass, 'manual_create', None)
        manual_update   = getattr(ni_metaclass, 'manual_update', None)

        # check for relationship processors and delete associated nodes functions
        relations_processors = getattr(ni_metaclass, 'relations_processors', None)
        delete_nodes         = getattr(ni_metaclass, 'delete_nodes', None)
        subentity_processors = getattr(ni_metaclass, 'subentity_processors', None)

        # we'll retrieve these values NI type/metatype from the GraphQLType
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()

        # specify and set create and update forms
        assert form and not create_form and not update_form or\
            create_form and update_form and not form, \
            'You must specify form or both create_form and edit_form in {}'\
            .format(cls.__name__)

        if form:
            create_form = form
            update_form = form

        # create mutations
        mutation_name_cc = node_type.title().replace(' ', ''  )

        if unique_node:
            cls.create_mutation_class = CreateUniqueNIMutation

        class_name = 'Create{}'.format(mutation_name_cc)
        attr_dict = {
            'django_form': create_form,
            'request_path': request_path,
            'is_create': True,
            'graphql_type': graphql_type,
            'include': create_include,
            'exclude': create_exclude,
            'property_update': property_update,
            'relay_extra_ids': relay_extra_ids,
        }

        if relations_processors:
            attr_dict['relations_processors'] = relations_processors

        if subentity_processors:
            attr_dict['subentity_processors'] = subentity_processors

        create_metaclass = type(metaclass_name, (object,), attr_dict)

        if not manual_create:
            cls._create_mutation = type(
                class_name,
                (cls.create_mutation_class,),
                {
                    metaclass_name: create_metaclass,
                },
            )
        else:
            cls._create_mutation = manual_create

        graphql_type.set_create_mutation(cls._create_mutation)

        class_name = 'Update{}'.format(mutation_name_cc)
        attr_dict['django_form']   = update_form
        attr_dict['is_create']     = False
        attr_dict['include']       = update_include
        attr_dict['exclude']       = update_exclude

        if relations_processors:
            attr_dict['relations_processors'] = relations_processors

        update_metaclass = type(metaclass_name, (object,), attr_dict)

        if not manual_update:
            cls._update_mutation = type(
                class_name,
                (cls.update_mutation_class,),
                {
                    metaclass_name: update_metaclass,
                },
            )
        else:
            cls._update_mutation = manual_update

        graphql_type.set_update_mutation(cls._update_mutation)

        class_name = 'Delete{}'.format(mutation_name_cc)
        del attr_dict['django_form']
        del attr_dict['include']
        del attr_dict['exclude']
        del attr_dict['property_update']
        del attr_dict['relay_extra_ids']
        attr_dict['is_delete'] = True

        if relations_processors:
            del attr_dict['relations_processors']

        if delete_nodes:
            attr_dict['delete_nodes'] = delete_nodes

        if subentity_processors:
            del attr_dict['subentity_processors']

        delete_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._delete_mutation = type(
            class_name,
            (cls.delete_mutation_class,),
            {
                metaclass_name: delete_metaclass,
            },
        )

        graphql_type.set_delete_mutation(cls._delete_mutation)

        # make multiple mutation
        class_name = 'Multiple{}'.format(mutation_name_cc)

        # create input class
        multi_attr_input_list = {
            'create_inputs': cls._create_mutation.NIMetaClass._input_list,
            'update_inputs': cls._update_mutation.NIMetaClass._input_list,
            'delete_inputs': cls._delete_mutation.NIMetaClass._input_list,
            'detach_inputs': graphene.List(DeleteRelationship.Input),
        }

        inner_class = type('Input', (object,), multi_attr_input_list)

        # metaclass
        metaclass_attr = {
            'create_mutation': cls._create_mutation,
            'update_mutation': cls._update_mutation,
            'delete_mutation': cls._delete_mutation,
            'detach_mutation': DeleteRelationship,
        }

        meta_class = type('NIMetaClass', (object,), metaclass_attr)

        # create class
        multiple_attr_list = {
            'Input': inner_class,
            'created': cls._create_mutation.NIMetaClass._payload_list,
            'updated': cls._update_mutation.NIMetaClass._payload_list,
            'deleted': cls._delete_mutation.NIMetaClass._payload_list,
            'detached': graphene.List(DeleteRelationship),
            'NIMetaClass': meta_class
        }

        cls._multiple_mutation = type(
            class_name,
            (MultipleMutation,),
            multiple_attr_list
        )


    @classmethod
    def get_create_mutation(cls, *args, **kwargs):
        return cls._create_mutation

    @classmethod
    def get_update_mutation(cls, *args, **kwargs):
        return cls._update_mutation

    @classmethod
    def get_delete_mutation(cls, *args, **kwargs):
        return cls._delete_mutation

    @classmethod
    def get_multiple_mutation(cls, *args, **kwargs):
        return cls._multiple_mutation

########## END MUTATION FACTORY

########## EXCEPTION
class GraphQLAuthException(Exception):
    '''
    Simple auth exception
    '''
    default_msg = 'You must be logged in the system: {}'

    def __init__(self, message=None):
        message = self.default_msg.format(
            ': {}'.format(message) if message else ''
        )
        super().__init__(message)

########## END EXCEPTION
