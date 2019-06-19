# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import norduniclient as nc
import re

from apps.noclook import helpers
from apps.noclook.models import NodeType, NodeHandle
from collections import OrderedDict
from django import forms
from django.db.models import Q
from django.test import RequestFactory
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions
from graphql import GraphQLError
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible

from ..models import NodeType, NodeHandle

def build_match_predicate(field, value, type):
    # string quoting
    if isinstance(type, graphene.String):
        value = "'{}'".format(value)

    ret = """n.{field} = {value}""".format(field=field, value=value)

    return ret

def build_not_predicate(field, value, type):
    # string quoting
    if isinstance(type, graphene.String):
        value = "'{}'".format(value)

    ret = """n.{field} <> {value}""".format(field=field, value=value)

    return ret

def build_in_predicate(field, values, type): # a list predicate builder
    # string quoting
    filter_strings = False
    if isinstance(type, graphene.String):
        filter_strings = True

    subpredicates = []
    for value in values:
        if filter_strings:
            value = "'{}'".format(value)
        subpredicates.append(
            """n.{field} = {value}""".format(field=field, value=value)
        )

    ret = ' OR '.join(subpredicates)
    return ret

def build_not_in_predicate(field, values, type): # a list predicate builder
    # string quoting
    filter_strings = False
    if isinstance(type, graphene.String):
        filter_strings = True

    subpredicates = []
    for value in values:
        if filter_strings:
            value = "'{}'".format(value)
        subpredicates.append(
            """n.{field} <> {value}""".format(field=field, value=value)
        )

    ret = ' AND '.join(subpredicates)
    return ret

def build_lt_predicate(field, value, type):
    # string quoting
    if isinstance(type, graphene.String):
        value = "'{}'".format(value)

    ret = """n.{field} < {value}""".format(field=field, value=value)

    return ret

def build_lte_predicate(field, value, type):
    # string quoting
    if isinstance(type, graphene.String):
        value = "'{}'".format(value)

    ret = """n.{field} <= {value}""".format(field=field, value=value)

    return ret

def build_gt_predicate(field, value, type):
    # string quoting
    if isinstance(type, graphene.String):
        value = "'{}'".format(value)

    ret = """n.{field} > {value}""".format(field=field, value=value)

    return ret

def build_gte_predicate(field, value, type):
    # string quoting
    if isinstance(type, graphene.String):
        value = "'{}'".format(value)

    ret = """n.{field} >= {value}""".format(field=field, value=value)

    return ret

def build_contains_predicate(field, value, type):
    return """n.{field} CONTAINS '{value}'""".format(field=field, value=value)

def build_not_contains_predicate(field, value, type):
    return """NOT n.{field} CONTAINS '{value}'""".format(field=field, value=value)

def build_starts_with_predicate(field, value, type):
    return """n.{field} STARTS WITH '{value}'""".format(field=field, value=value)

def build_not_starts_with_predicate(field, value, type):
    return """NOT n.{field} STARTS WITH '{value}'""".format(field=field, value=value)

def build_ends_with_predicate(field, value, type):
    return """n.{field} ENDS WITH '{value}'""".format(field=field, value=value)

def build_not_ends_with_predicate(field, value, type):
    return """NOT n.{field} ENDS WITH '{value}'""".format(field=field, value=value)

filter_array = {
    '':       { 'wrapper_field': None, 'only_strings': False, 'qpredicate': build_match_predicate },
    'not':    { 'wrapper_field': None, 'only_strings': False, 'qpredicate': build_not_predicate },
    'in':     { 'wrapper_field': [graphene.NonNull, graphene.List], 'only_strings': False, 'qpredicate': build_in_predicate },
    'not_in': { 'wrapper_field': [graphene.NonNull, graphene.List], 'only_strings': False, 'qpredicate': build_not_in_predicate },
    'lt':     { 'wrapper_field': None, 'only_strings': False, 'qpredicate': build_lt_predicate },
    'lte':    { 'wrapper_field': None, 'only_strings': False, 'qpredicate': build_lte_predicate },
    'gt':     { 'wrapper_field': None, 'only_strings': False, 'qpredicate': build_gt_predicate },
    'gte':    { 'wrapper_field': None, 'only_strings': False, 'qpredicate': build_gte_predicate },

    'contains':        { 'wrapper_field': None, 'only_strings': True, 'qpredicate': build_contains_predicate },
    'not_contains':    { 'wrapper_field': None, 'only_strings': True, 'qpredicate': build_not_contains_predicate },
    'starts_with':     { 'wrapper_field': None, 'only_strings': True, 'qpredicate': build_starts_with_predicate },
    'not_starts_with': { 'wrapper_field': None, 'only_strings': True, 'qpredicate': build_not_starts_with_predicate },
    'ends_with':       { 'wrapper_field': None, 'only_strings': True, 'qpredicate': build_ends_with_predicate },
    'not_ends_with':   { 'wrapper_field': None, 'only_strings': True, 'qpredicate': build_not_ends_with_predicate },
}

class KeyValue(graphene.Interface):
    name = graphene.String(required=True)
    value = graphene.String(required=True)

class DictEntryType(graphene.ObjectType):
    '''
    This type represents an key value pair in a dictionary for the data
    dict of the norduniclient nodes
    '''

    class Meta:
        interfaces = (KeyValue, )

def resolve_nidata(self, info, **kwargs):
    '''
    Resolvers norduniclient nodes data dictionary
    '''
    ret = []

    alldata = self.get_node().data
    for key, value in alldata.items():
        ret.append(DictEntryType(key=key, value=value))

    return ret

class NIBasicField():
    '''
    Super class of the type fields
    '''
    def __init__(self, field_type=graphene.String, manual_resolver=False,
                    type_kwargs=None, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_kwargs     = type_kwargs

    def get_resolver(self, **kwargs):
        field_name = kwargs.get('field_name')
        if not field_name:
            raise Exception(
                'Field name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )
        def resolve_node_value(self, info, **kwargs):
            return self.get_node().data.get(field_name)

        return resolve_node_value

    def get_field_type(self):
        return self.field_type

class NIStringField(NIBasicField):
    '''
    String type
    '''
    pass

class NIIntField(NIBasicField):
    '''
    Int type
    '''
    def __init__(self, field_type=graphene.Int, manual_resolver=False,
                    type_kwargs=None, **kwargs):
        super(NIIntField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)

class NIListField(NIBasicField):
    '''
    Object list type
    '''
    def __init__(self, field_type=graphene.List, manual_resolver=False,
                    type_args=None, rel_name=None, rel_method=None,
                    not_null_list=False, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_args       = type_args
        self.rel_name        = rel_name
        self.rel_method      = rel_method
        self.not_null_list   = not_null_list

    def get_resolver(self, **kwargs):
        rel_name   = kwargs.get('rel_name')
        rel_method = kwargs.get('rel_method')

        def resolve_relationship_list(self, info, **kwargs):
            neo4jnode = self.get_node()
            relations = getattr(neo4jnode, rel_method)()
            nodes = relations.get(rel_name)

            # this may be the worst way to do it, but it's just for a PoC
            handle_id_list = []
            if nodes:
                for node in nodes:
                    node = node['node']
                    node_id = node.data.get('handle_id')
                    handle_id_list.append(node_id)

            ret = NodeHandle.objects.filter(handle_id__in=handle_id_list)

            return ret

        return resolve_relationship_list

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
    start = graphene.Field(graphene.Int, required=True)
    end = graphene.Field(graphene.Int, required=True)
    nidata = graphene.List(DictEntryType)

    def resolve_relation_id(self, info, **kwargs):
        self.relation_id = self.id
        self.id = None

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

    class Meta:
        interfaces = (relay.Node, )

class DictRelationType(graphene.ObjectType):
    '''
    This type represents an key value pair for a relationship dictionary,
    the key is the name of the relationship and the value the NIRelationType itself
    '''
    name = graphene.String(required=True)
    relation = graphene.Field(NIRelationType, required=True)

class NIObjectType(DjangoObjectType):
    '''
    This class expands graphene_django object type adding the defined fields in
    the types subclasses and extracts the data from the norduniclient nodes and
    adds a resolver for each field, a nidata field is also added to hold the
    values of the node data dict.
    '''

    filter_names = None

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

            # adding the field
            field_value = None
            if type_kwargs:
                field_value = field_type(**type_kwargs)
            elif type_args:
                field_value = field_type(*type_args)
                if not_null_list:
                    field_value = graphene.NonNull(field_type(*type_args))
            else:
                field_value = field_type(**{})

            setattr(cls, name, field_value)

            # adding the resolver
            if not manual_resolver:
                setattr(cls, 'resolve_{}'.format(name), \
                    field.get_resolver(
                        field_name=name,
                        rel_name=rel_name,
                        rel_method=rel_method,
                    )
                )

            elif callable(manual_resolver):
                setattr(cls, 'resolve_{}'.format(name), manual_resolver)
            else:
                raise Exception(
                    'NIObjectField manual_resolver must be a callable in field {}'\
                        .format(name)
                )

        options['model'] = NIObjectType._meta.model
        options['interfaces'] = NIObjectType._meta.interfaces

        super(NIObjectType, cls).__init_subclass_with_meta__(
            **options
        )

    nidata = graphene.List(DictEntryType, resolver=resolve_nidata)

    incoming = graphene.List(DictRelationType)
    outgoing = graphene.List(DictRelationType)

    def resolve_incoming(self, info, **kwargs):
        '''
        Resolver for incoming relationships for the node
        '''
        incoming_rels = self.get_node().incoming
        ret = []
        for rel_name, rel in incoming_rels.items():
            relation_id = rel[0]['relationship_id']
            rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
            ret.append(DictRelationType(name=rel_name, relation=rel))

        return ret

    def resolve_outgoing(self, info, **kwargs):
        '''
        Resolver for outgoing relationships for the node
        '''
        outgoing_rels = self.get_node().outgoing
        ret = []
        for rel_name, rel in outgoing_rels.items():
            relation_id = rel[0]['relationship_id']
            rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
            ret.append(DictRelationType(name=rel_name, relation=rel))

        return ret

    @classmethod
    def get_from_nimetatype(cls, attr):
        ni_metatype = getattr(cls, 'NIMetaType')
        return getattr(ni_metatype, attr)

    @classmethod
    def get_type_name(cls):
        ni_type = cls.get_from_nimetatype('ni_type')
        node_type = NodeType.objects.filter(type=ni_type).first()
        return node_type.type

    @classmethod
    def get_filter_input_fields(cls):
        '''
        Method used by build_filter_and_order
        '''
        input_fields = {}

        for name, field in cls.__dict__.items():
            if field and not isinstance(field, str) and getattr(field, '__module__', None) == 'graphene.types.scalars':
                input_field = type(field)
                input_fields[name] = input_field

        input_fields['handle_id'] = graphene.Int

        return input_fields

    @classmethod
    def build_filter_and_order(cls):
        '''
        This method generates a Filter and Order object from the class itself
        to be used in filtering connections
        '''
        ni_type = cls.get_from_nimetatype('ni_type')

        # build filter input class and order enum
        filter_attrib = {}
        cls.filter_names = {}
        enum_options = []
        input_fields = cls.get_filter_input_fields()

        for field_name, input_field in input_fields.items():
            # adding order attributes
            enum_options.append(['{}_ASC'.format(field_name), '{}_ASC'.format(field_name)])
            enum_options.append(['{}_DESC'.format(field_name), '{}_DESC'.format(field_name)])

            # adding filter attributes
            for suffix, suffix_attr in filter_array.items():
                if not suffix == '':
                    suffix = '_{}'.format(suffix)

                fmt_filter_field = '{}{}'.format(field_name, suffix)

                if not suffix_attr['only_strings'] or isinstance(input_field(), graphene.String):
                    if 'wrapper_field' not in suffix_attr or not suffix_attr['wrapper_field']:
                        filter_attrib[fmt_filter_field] = input_field()
                        cls.filter_names[fmt_filter_field]  = {
                            'field' : field_name,
                            'suffix': suffix,
                            'field_type': input_field(),
                        }
                    else:
                        the_field = input_field
                        for wrapper_field in suffix_attr['wrapper_field']:
                            the_field = wrapper_field(the_field)

                        filter_attrib[fmt_filter_field] = the_field
                        cls.filter_names[fmt_filter_field]  = {
                            'field' : field_name,
                            'suffix': suffix,
                            'field_type': input_field(),
                        }

        simple_filter_input = type('{}NestedFilter'.format(ni_type), (graphene.InputObjectType, ), filter_attrib)

        filter_attrib = {}
        filter_attrib['AND'] = graphene.List(graphene.NonNull(simple_filter_input))
        filter_attrib['OR'] = graphene.List(graphene.NonNull(simple_filter_input))

        filter_input = type('{}Filter'.format(ni_type), (graphene.InputObjectType, ), filter_attrib)

        orderBy = graphene.Enum('{}OrderBy'.format(ni_type), enum_options)

        return filter_input, orderBy

    @classmethod
    def get_byid_resolver(cls):
        type_name = cls.get_type_name()

        def generic_byid_resolver(self, info, **args):
            handle_id = args.get('handle_id')
            node_type = NodeType.objects.get(type=type_name)

            ret = None

            if info.context and info.context.user.is_authenticated:
                if handle_id:
                    ret = NodeHandle.objects.filter(node_type=node_type).get(handle_id=handle_id)
                else:
                    raise GraphQLError('A handle_id must be provided')

                if not ret:
                    raise GraphQLError("There isn't any {} with handle_id {}".format(type_name, handle_id))

                return ret
            else:
                raise GraphQLAuthException()

        return generic_byid_resolver

    @classmethod
    def get_connection_resolver(cls):
        type_name = cls.get_type_name()

        def generic_list_resolver(self, info, **args):
            ret = None
            filter  = args.get('filter', None)
            orderBy = args.get('orderBy', None)

            if info.context and info.context.user.is_authenticated:
                # filtering will take a different approach
                nodes = None
                if filter:
                    q = cls.build_filter_query(filter, type_name)
                    nodes = nc.query_to_list(nc.graphdb.manager, q)
                    nodes = [ node['n'].properties for node in nodes]
                else:
                    nodes = nc.get_nodes_by_type(nc.graphdb.manager, type_name)
                    nodes = list(nodes)

                if nodes:
                    handle_ids = []
                    # ordering
                    if orderBy:
                        m = re.match(r"([\w|\_]*)_(ASC|DESC)", orderBy)
                        prop = m[1]
                        order = m[2]
                        reverse = True if order == 'DESC' else False
                        nodes.sort(key=lambda x: x.get(prop, ''), reverse=reverse)
                        handle_ids = [ node['handle_id'] for node in nodes ]
                    else:
                        handle_ids = [ node['handle_id'] for node in nodes ]
                        node_type = NodeType.objects.get(type=type_name)

                    ret = [ NodeHandle.objects.get(handle_id=handle_id) for handle_id in handle_ids ]

                if not ret:
                    ret = []

                return ret
            else:
                raise GraphQLAuthException()

        return generic_list_resolver

    @classmethod
    def build_filter_query(cls, filter, nodetype):
        build_query = ''

        # build AND block
        and_filters = filter.get('AND', [])
        and_predicates = []

        # iterate through the nested filters
        for and_filter in and_filters:
            # iterate though values of a nested filter
            for filter_key, filter_value in and_filter.items():
                filter_field = cls.filter_names[filter_key]
                field  = filter_field['field']
                suffix = filter_field['suffix']
                field_type = filter_field['field_type']

                # iterate through the keys of the filter array and extracts
                # the predicate building function
                for fa_suffix, fa_value in filter_array.items():
                    if fa_suffix != '':
                         fa_suffix = '_{}'.format(fa_suffix)

                    # get the predicate
                    if suffix == fa_suffix:
                        build_preficate_func = fa_value['qpredicate']
                        predicate = build_preficate_func(field, filter_value, field_type)
                        if predicate:
                            and_predicates.append(predicate)

        # build OR block
        or_filters = filter.get('OR', [])
        or_predicates = []

        for or_filter in or_filters:
            # iterate though values of a nested filter
            for filter_key, filter_value in or_filter.items():
                filter_field = cls.filter_names[filter_key]
                field  = filter_field['field']
                suffix = filter_field['suffix']
                field_type = filter_field['field_type']

                # iterate through the keys of the filter array and extracts
                # the predicate building function
                for fa_suffix, fa_value in filter_array.items():
                    if fa_suffix != '':
                         fa_suffix = '_{}'.format(fa_suffix)

                    # get the predicate
                    if suffix == fa_suffix:
                        build_preficate_func = fa_value['qpredicate']
                        predicate = build_preficate_func(field, filter_value, field_type)
                        if predicate:
                            or_predicates.append(predicate)

        and_query = ' AND '.join(and_predicates)
        or_query = ' OR '.join(or_predicates)

        if and_query and or_query:
            build_query = '{} OR {}'.format(
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

        q = """
            MATCH (n:{label})
            {build_query}
            RETURN distinct n
            """.format(label=nodetype, build_query=build_query)

        return q

    class Meta:
        model = NodeHandle
        interfaces = (relay.Node, )

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
            nimeta = getattr(rel_type, 'NIMeta', None)
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

class NodeHandler(NIObjectType):
    name = NIStringField(type_kwargs={ 'required': True })

class AbstractNIMutation(relay.ClientIDMutation):
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
                            elif include:
                                if field_name in include:
                                    add_field = True
                            elif exclude:
                                if field_name not in exclude:
                                    add_field = True
                            else:
                                add_field = True

                            if add_field:
                                inner_fields[field_name] = graphene_field

        # add handle_id
        if not is_create:
            inner_fields['handle_id'] = graphene.Int(required=True)

        # add Input attribute to class
        inner_class = type('Input', (object,), inner_fields)
        setattr(cls, 'Input', inner_class)

        cls.add_return_type(graphql_type)

        super(AbstractNIMutation, cls).__init_subclass_with_meta__(
            output, inner_fields, arguments, name=mutation_name, **options
        )

    @classmethod
    def add_return_type(cls, graphql_type):
        if graphql_type:
            setattr(cls, graphql_type.__name__.lower(), graphene.Field(graphql_type))

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
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.FloatField):
                graphene_field = graphene.Float(**graph_kwargs)
            elif isinstance(form_field, forms.IntegerField):
                graphene_field = graphene.Int(**graph_kwargs)
            elif isinstance(form_field, forms.MultipleChoiceField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.NullBooleanField):
                graphene_field = graphene.String(**graph_kwargs)
            elif isinstance(form_field, forms.URLField):
                graphene_field = graphene.String(**graph_kwargs)
            else:
                graphene_field = graphene.String(**graph_kwargs)

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

        graphql_type   = getattr(ni_metaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()

        # get input values
        input_class = getattr(cls, 'Input', None)
        input_params = {}
        if input_class:
            for attr_name, attr_field in input_class.__dict__.items():
                attr_value = input.get(attr_name)
                if attr_value:
                    input_params[attr_name] = attr_value

        if not is_create:
            input_params['handle_id'] = input.get('handle_id')

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

        reqinput = cls.from_input_to_request(info.context.user, **input)
        ret = cls.do_request(reqinput[0], **reqinput[1])

        graphql_type = cls.get_graphql_type()
        init_params = {}
        for key, value in ret.items():
            init_params[key] = value

        return cls(**init_params)

    @classmethod
    def get_graphql_type(cls):
        ni_metaclass  = getattr(cls, 'NIMetaClass')
        graphql_type  = getattr(ni_metaclass, 'graphql_type', None)

        return graphql_type

    class Meta:
        abstract = True

class CreateNIMutation(AbstractNIMutation):
    '''
    This class is used by the Mutation factory but it could be used as the
    superclass of a manualy coded class in case it's needed.
    '''
    class NIMetaClass:
        request_path   = None
        is_create      = True
        graphql_type   = None
        include        = None
        exclude        = None

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()

        ## code from role creation
        form = form_class(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form,
                        node_type, node_meta_type)
            except UniqueNodeError:
                raise GraphQLError(
                    'A {} with that name already exists.'.format(node_type)
                )
            helpers.form_update_node(request.user, nh.handle_id, form)
            return { graphql_type.__name__.lower(): nh }
        else:
            # get the errors and return them
            raise GraphQLError('Form errors: {}'.format(form.errors))

class UpdateNIMutation(AbstractNIMutation):
    class NIMetaClass:
        request_path   = None
        graphql_type   = None
        include        = None
        exclude        = None

    @classmethod
    def do_request(cls, request, **kwargs):
        form_class     = kwargs.get('form_class')
        nimetaclass    = getattr(cls, 'NIMetaClass')
        graphql_type   = getattr(nimetaclass, 'graphql_type')
        nimetatype     = getattr(graphql_type, 'NIMetaType')
        node_type      = getattr(nimetatype, 'ni_type').lower()
        node_meta_type = getattr(nimetatype, 'ni_metatype').capitalize()
        handle_id      = request.POST.get('handle_id')

        nh, nodehandler = helpers.get_nh_node(handle_id)
        if request.POST:
            form = form_class(request.POST)
            if form.is_valid():
                # Generic node update
                helpers.form_update_node(request.user, nodehandler.handle_id, form)

                # process relations if implemented
                cls.process_relations(request, form, nodehandler)

                return { graphql_type.__name__.lower(): nh }
            else:
                raise GraphQLError('Form is not valid: {}'.format(form.errors))
        else:
            # get the errors and return them
            raise GraphQLError('Form errors: {}'.format(form.errors))

    @classmethod
    def process_relations(cls, request, form, nodehandler):
        from pprint import pformat
        nimetaclass = getattr(cls, 'NIMetaClass')
        relations_processors = getattr(nimetaclass, 'relations_processors', None)

        if relations_processors:
            for relation_name, relation_f in relations_processors.items():
                relation_f(request, form, nodehandler, relation_name)

class DeleteNIMutation(AbstractNIMutation):
    class NIMetaClass:
        request_path   = None
        graphql_type   = None

    @classmethod
    def add_return_type(cls, graphql_type):
        setattr(cls, 'success', graphene.Boolean(required=True))

    @classmethod
    def do_request(cls, request, **kwargs):
        handle_id      = request.POST.get('handle_id')

        nh, node = helpers.get_nh_node(handle_id)
        success = helpers.delete_node(request.user, node.handle_id)

        return {'success': success}

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
        ni_metaclass   = getattr(cls, metaclass_name)
        form           = getattr(ni_metaclass, 'form', None)
        create_form    = getattr(ni_metaclass, 'create_form', None)
        update_form    = getattr(ni_metaclass, 'update_form', None)
        request_path   = getattr(ni_metaclass, 'request_path', None)
        graphql_type   = getattr(ni_metaclass, 'graphql_type', NodeHandler)
        create_include = getattr(ni_metaclass, 'create_include', None)
        create_exclude = getattr(ni_metaclass, 'create_exclude', None)
        update_include = getattr(ni_metaclass, 'update_include', None)
        update_exclude = getattr(ni_metaclass, 'update_exclude', None)

        # check for relationship processors
        relations_processors = getattr(ni_metaclass, 'relations_processors', None)

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
        class_name = 'CreateNI{}Mutation'.format(node_type.capitalize())
        attr_dict = {
            'django_form': create_form,
            'request_path': request_path,
            'is_create': True,
            'graphql_type': graphql_type,
            'include': create_include,
            'exclude': create_exclude,
        }

        create_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._create_mutation = type(
            class_name,
            (cls.create_mutation_class,),
            {
                metaclass_name: create_metaclass,
            },
        )

        class_name = 'UpdateNI{}Mutation'.format(node_type.capitalize())
        attr_dict['django_form']   = update_form
        attr_dict['is_create']     = False
        attr_dict['include']       = update_include
        attr_dict['exclude']       = update_exclude

        if relations_processors:
            attr_dict['relations_processors'] = relations_processors

        update_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._update_mutation = type(
            class_name,
            (cls.update_mutation_class,),
            {
                metaclass_name: update_metaclass,
            },
        )

        class_name = 'DeleteNI{}Mutation'.format(node_type.capitalize())
        del attr_dict['django_form']
        del attr_dict['include']
        del attr_dict['exclude']

        if relations_processors:
            del attr_dict['relations_processors']

        delete_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._delete_mutation = type(
            class_name,
            (cls.delete_mutation_class,),
            {
                metaclass_name: delete_metaclass,
            },
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

# TODO: create a new mutation factory for relationships types
# update relationship attributes or delete the relation itself
# what about creating relationships between two related entities?

class GraphQLAuthException(Exception):
    '''
    Simple auth exception
    '''
    def __init__(self, message=None):
        message = 'You must be logged in the system: {}'.format(
            ': {}'.format(message) if message else ''
        )
        super().__init__(message)

class NOCAutoQuery(graphene.ObjectType):
    '''
    This class creates a connection and a getById method for each of the types
    declared on the graphql_types of the NIMeta class of any subclass.
    '''
    node = relay.Node.Field()
    getNodeById = graphene.Field(NodeHandler, handle_id=graphene.Int())

    def resolve_getNodeById(self, info, **args):
        handle_id = args.get('handle_id')

        ret = None

        if info.context and info.context.user.is_authenticated:
            if handle_id:
                ret = NodeHandle.objects.get(handle_id=handle_id)
            else:
                raise GraphQLError('A valid handle_id must be provided')

            if not ret:
                raise GraphQLError("There isn't any {} with handle_id {}".format(nodetype, handle_id))

            return ret
        else:
            raise GraphQLAuthException()


    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        _nimeta = getattr(cls, 'NIMeta')
        graphql_types = getattr(_nimeta, 'graphql_types')

        assert graphql_types, \
            'A tuple with the types should be set in the Meta class of {}'.format(cls.__name__)

        # add list with pagination resolver
        # add by id resolver
        for graphql_type in graphql_types:
            ## extract values
            ni_type = graphql_type.get_from_nimetatype('ni_type')
            assert ni_type, '{} has not set its ni_type attribute'.format(cls.__name__)
            ni_metatype = graphql_type.get_from_nimetatype('ni_metatype')
            assert ni_metatype, '{} has not set its ni_metatype attribute'.format(cls.__name__)

            node_type     = NodeType.objects.filter(type=ni_type).first()
            type_name     = node_type.type
            type_slug     = node_type.slug

            # add connection attribute
            field_name    = '{}s'.format(type_slug)
            resolver_name = 'resolve_{}'.format(field_name)

            connection_input, connection_order = graphql_type.build_filter_and_order()
            connection_meta = type('Meta', (object, ), dict(node=graphql_type))
            connection_class = type(
                '{}Connection'.format(graphql_type.__name__),
                (graphene.relay.Connection,),
                #(connection_type,),
                dict(Meta=connection_meta)
            )

            setattr(cls, field_name, graphene.relay.ConnectionField(
                connection_class,
                filter=graphene.Argument(connection_input),
                orderBy=graphene.Argument(connection_order),
            ))
            setattr(cls, resolver_name, graphql_type.get_connection_resolver())

            ## build field and resolver byid
            field_name    = 'get{}ById'.format(type_name)
            resolver_name = 'resolve_{}'.format(field_name)

            setattr(cls, field_name, graphene.Field(graphql_type, handle_id=graphene.Int()))
            setattr(cls, resolver_name, graphql_type.get_byid_resolver())
