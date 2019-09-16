# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import datetime
import graphene
import norduniclient as nc
import re

from apps.noclook import helpers
from apps.noclook.models import NodeType, NodeHandle
from collections import OrderedDict, Iterable
from django import forms
from django.contrib.auth.models import User as DjangoUser
from django.db.models import Q
from django.forms.utils import ValidationError
from django.test import RequestFactory
from django.utils import six
from django_comments.models import Comment
from graphene import relay
from graphene.types import Scalar, DateTime
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions, ErrorType
from graphql import GraphQLError
from graphql.language.ast import IntValue, StringValue
from io import StringIO
from norduniclient.exceptions import UniqueNodeError, NoRelationshipPossible

from ..models import NodeType, NodeHandle

########## CUSTOM SCALARS FOR FORM FIELD CONVERSION
class IPAddr(Scalar):
    '''IPAddr scalar to be matched with the IPAddrField in a django form'''
    @staticmethod
    def serialize(value):
        # this would be to_python method
        if isinstance(value, list):
            return value
        else:
            return none

    @staticmethod
    def parse_value(value):
        # and this would be the clean method
        result = []
        for line in StringIO(value):
            ip = line.replace('\n','').strip()
            if ip:
                try:
                    ipaddress.ip_address(ip)
                    result.append(ip)
                except ValueError as e:
                    errors.append(str(e))
        if errors:
            raise ValidationError(errors)
        return result

    parse_literal = parse_value


class JSON(Scalar):
    '''JSON scalar to be matched with the JSONField in a django form'''
    @staticmethod
    def serialize(value):
        if value:
            value = json.dumps(value)

        return value

    @staticmethod
    def parse_value(value):
        try:
            if value:
                value = json.loads(value)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return value

"""class DateTime(Scalar):
    # http://docs.graphene-python.org/en/latest/types/scalars/#custom-scalars
    '''DateTime Scalar Description'''

    @staticmethod
    def serialize(dt):
        return dt.isoformat()

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.StringValue):
            return datetime.datetime.strptime(
                node.value, "%Y-%m-%dT%H:%M:%S.%f")

    @staticmethod
    def parse_value(value):
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")"""

class RoleScalar(Scalar):
    '''This is a POC scalar that may be used in the contact mutation input'''
    @staticmethod
    def serialize(value):
        roles_dict = get_roles_dropdown()

        if value in roles_dict.keys():
            return roles_dict[value]
        else:
            raise Exception('The selected role ("{}") doesn\'t exists'
                                .format(value))

    @staticmethod
    def parse_value(value):
        roles_dict = get_roles_dropdown()

        key = value.replace(' ', '_').lower()
        if key in roles_dict.keys():
            return roles_dict[key]
        else:
            return value

    @staticmethod
    def get_roles_dropdown():
        ret = {}
        roles = nc.models.RoleRelationship.get_all_roles()
        for role in roles:
            name = role.replace(' ', '_').lower()
            ret[name] = role

        return ret

class ChoiceScalar(Scalar):
    '''This scalar represents a choice field in query/mutation'''
    @staticmethod
    def coerce_choice(value):
        num = None
        try:
            num = int(value)
        except ValueError:
            try:
                num = int(float(value))
            except ValueError:
                pass
        if num:
            return graphene.Int.coerce_int(value)
        else:
            return graphene.String.coerce_string(value)


    serialize = coerce_choice
    parse_value = coerce_choice

    @staticmethod
    def parse_literal(ast):
        if isinstance(ast, IntValue):
            return graphene.Int.parse_literal(ast)
        elif isinstance(ast, StringValue):
            return graphene.String.parse_literal(ast)

    @classmethod
    def get_roles_dropdown(cls):
        pass

########## END CUSTOM SCALARS FOR FORM FIELD CONVERSION

########## CONNECTION FILTER BUILD FUNCTIONS
class classproperty(object):
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)

class AbstractQueryBuilder:
    @staticmethod
    def build_match_predicate(field, value, type):
        pass

    @staticmethod
    def build_not_predicate(field, value, type):
        pass

    @staticmethod
    def build_in_predicate(field, value, type):
        pass

    @staticmethod
    def build_not_in_predicate(field, value, type):
        pass

    @staticmethod
    def build_lt_predicate(field, value, type):
        pass

    @staticmethod
    def build_lte_predicate(field, value, type):
        pass

    @staticmethod
    def build_gt_predicate(field, value, type):
        pass

    @staticmethod
    def build_gte_predicate(field, value, type):
        pass

    @staticmethod
    def build_contains_predicate(field, value, type):
        pass

    @staticmethod
    def build_not_contains_predicate(field, value, type):
        pass

    @staticmethod
    def build_starts_with_predicate(field, value, type):
        pass

    @staticmethod
    def build_not_starts_with_predicate(field, value, type):
        pass

    @staticmethod
    def build_ends_with_predicate(field, value, type):
        pass

    @staticmethod
    def build_not_ends_with_predicate(field, value, type):
        pass

    @classproperty
    def filter_array(cls):
        return OrderedDict([
            ('',       { 'wrapper_field': None, 'only_strings': False, 'qpredicate': cls.build_match_predicate }),
            ('not',    { 'wrapper_field': None, 'only_strings': False, 'qpredicate': cls.build_not_predicate }),
            ('in',     { 'wrapper_field': [graphene.NonNull, graphene.List], 'only_strings': False, 'qpredicate': cls.build_in_predicate }),
            ('not_in', { 'wrapper_field': [graphene.NonNull, graphene.List], 'only_strings': False, 'qpredicate': cls.build_not_in_predicate }),
            ('lt',     { 'wrapper_field': None, 'only_strings': False, 'qpredicate': cls.build_lt_predicate }),
            ('lte',    { 'wrapper_field': None, 'only_strings': False, 'qpredicate': cls.build_lte_predicate }),
            ('gt',     { 'wrapper_field': None, 'only_strings': False, 'qpredicate': cls.build_gt_predicate }),
            ('gte',    { 'wrapper_field': None, 'only_strings': False, 'qpredicate': cls.build_gte_predicate }),

            ('contains',        { 'wrapper_field': None, 'only_strings': True, 'qpredicate': cls.build_contains_predicate }),
            ('not_contains',    { 'wrapper_field': None, 'only_strings': True, 'qpredicate': cls.build_not_contains_predicate }),
            ('starts_with',     { 'wrapper_field': None, 'only_strings': True, 'qpredicate': cls.build_starts_with_predicate }),
            ('not_starts_with', { 'wrapper_field': None, 'only_strings': True, 'qpredicate': cls.build_not_starts_with_predicate }),
            ('ends_with',       { 'wrapper_field': None, 'only_strings': True, 'qpredicate': cls.build_ends_with_predicate }),
            ('not_ends_with',   { 'wrapper_field': None, 'only_strings': True, 'qpredicate': cls.build_not_ends_with_predicate }),
        ])

class ScalarQueryBuilder(AbstractQueryBuilder):
    @staticmethod
    def build_match_predicate(field, value, type, **kwargs):
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)

        ret = """n.{field} = {value}""".format(field=field, value=value)

        return ret

    @staticmethod
    def build_not_predicate(field, value, type, **kwargs):
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)

        ret = """n.{field} <> {value}""".format(field=field, value=value)

        return ret

    @staticmethod
    def build_in_predicate(field, values, type, **kwargs): # a list predicate builder
        in_string = '{}'.format(', '.join(["'{}'".format(str(x)) for x in values]))
        ret = 'n.{field} IN [{in_string}]'.format(field=field, in_string=in_string)
        return ret

    @staticmethod
    def build_not_in_predicate(field, values, type, **kwargs): # a list predicate builder
        in_string = '{}'.format(', '.join(["'{}'".format(str(x)) for x in values]))
        ret = 'NOT n.{field} IN [{in_string}]'.format(field=field, in_string=in_string)
        return ret

    @staticmethod
    def build_lt_predicate(field, value, type, **kwargs):
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)

        ret = """n.{field} < {value}""".format(field=field, value=value)

        return ret

    @staticmethod
    def build_lte_predicate(field, value, type, **kwargs):
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)

        ret = """n.{field} <= {value}""".format(field=field, value=value)

        return ret

    @staticmethod
    def build_gt_predicate(field, value, type, **kwargs):
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)

        ret = """n.{field} > {value}""".format(field=field, value=value)

        return ret

    @staticmethod
    def build_gte_predicate(field, value, type, **kwargs):
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)

        ret = """n.{field} >= {value}""".format(field=field, value=value)

        return ret

    @staticmethod
    def build_contains_predicate(field, value, type, **kwargs):
        return """n.{field} CONTAINS '{value}'""".format(field=field, value=value)

    @staticmethod
    def build_not_contains_predicate(field, value, type, **kwargs):
        return """NOT n.{field} CONTAINS '{value}'""".format(field=field, value=value)

    @staticmethod
    def build_starts_with_predicate(field, value, type, **kwargs):
        return """n.{field} STARTS WITH '{value}'""".format(field=field, value=value)

    @staticmethod
    def build_not_starts_with_predicate(field, value, type, **kwargs):
        return """NOT n.{field} STARTS WITH '{value}'""".format(field=field, value=value)

    @staticmethod
    def build_ends_with_predicate(field, value, type, **kwargs):
        return """n.{field} ENDS WITH '{value}'""".format(field=field, value=value)

    @staticmethod
    def build_not_ends_with_predicate(field, value, type, **kwargs):
        return """NOT n.{field} ENDS WITH '{value}'""".format(field=field, value=value)

class InputFieldQueryBuilder(AbstractQueryBuilder):
    standard_expression = """{neo4j_var}.{field} {op} {value}"""
    id_expression = """ID({neo4j_var}) {op} {value}"""

    @classmethod
    def format_expression(cls, key, value, neo4j_var, op, add_quotes=True):
        # string quoting
        if isinstance(value, str) and add_quotes:
            value = "'{}'".format(value)

        if key is 'relation_id':
            ret = cls.id_expression.format(
                neo4j_var=neo4j_var,
                op=op,
                value=value,
            )
        else:
            ret = cls.standard_expression.format(
                neo4j_var=neo4j_var,
                field=key,
                op=op,
                value=value,
            )

        return ret

    @staticmethod
    def single_value_predicate(field, value, type, op, not_in=False, **kwargs):
        neo4j_var = kwargs.get('neo4j_var')
        ret = ""

        for k, v in value.items():
            ret = InputFieldQueryBuilder.format_expression(k, v, neo4j_var, op)

        if not_in:
            ret = 'NOT {}'.format(ret)

        return ret

    @classmethod
    def multiple_value_predicate(cls, field, values, type, op, not_in=False, **kwargs): # a list predicate builder
        neo4j_var = kwargs.get('neo4j_var')

        all_values = []
        field_name = ""

        for value in values:
            for k, v in value.items():
                if isinstance(v, str):
                    v = "'{}'".format(v)

                field_name = k
                all_values.append(v)

        the_value = "[{}]".format(', '.join([str(x) for x in all_values]))

        ret = InputFieldQueryBuilder.format_expression(field_name, the_value, neo4j_var, op, False)

        if not_in:
            ret = 'NOT {}'.format(ret)

        return ret

    @staticmethod
    def build_match_predicate(field, value, type, **kwargs):
        op = "="
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_not_predicate(field, value, type, **kwargs):
        op = "<>"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @classmethod
    def build_in_predicate(cls, field, values, type, **kwargs): # a list predicate builder
        op = "IN"
        ret = InputFieldQueryBuilder.multiple_value_predicate(
            field, values, type, op, **kwargs
        )
        return ret

    @classmethod
    def build_not_in_predicate(cls, field, values, type, **kwargs): # a list predicate builder
        op = "IN"
        ret = InputFieldQueryBuilder.multiple_value_predicate(
            field, values, type, op, True, **kwargs
        )
        return ret

    @staticmethod
    def build_lt_predicate(field, value, type, **kwargs):
        op = "<"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_lte_predicate(field, value, type, **kwargs):
        op = "<="
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_gt_predicate(field, value, type, **kwargs):
        op = ">"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_gte_predicate(field, value, type, **kwargs):
        op = ">="
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_contains_predicate(field, value, type):
        op = "CONTAINS"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_not_contains_predicate(field, value, type):
        op = "CONTAINS"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, True, **kwargs)

        return ret

    @staticmethod
    def build_starts_with_predicate(field, value, type):
        op = "STARTS WITH"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_not_starts_with_predicate(field, value, type):
        op = "STARTS WITH"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, True, **kwargs)

        return ret

    @staticmethod
    def build_ends_with_predicate(field, value, type):
        op = "ENDS WITH"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, **kwargs)

        return ret

    @staticmethod
    def build_not_ends_with_predicate(field, value, type):
        op = "ENDS WITH"
        ret = InputFieldQueryBuilder.single_value_predicate(field, value, type,
                                                                op, True, **kwargs)

        return ret


class DateQueryBuilder(AbstractQueryBuilder):
    fields = [ 'created', 'modified' ]

    @classproperty
    def suffixes(cls):
        '''
        The advantage of this over a static dict is that if the filter_array
        is changed in the superclass this would
        '''
        ret = OrderedDict()

        thekeys = list(cls.filter_array.keys())[:8]

        for akey in thekeys:
            if akey == '':
                ret[akey] = cls.build_match_predicate
            elif akey == 'not':
                ret[akey] = cls.build_not_predicate
            elif akey == 'in':
                ret[akey] = cls.build_in_predicate
            elif akey == 'not_in':
                ret[akey] = cls.build_not_in_predicate
            elif akey == 'lt':
                ret[akey] = cls.build_lt_predicate
            elif akey == 'lte':
                ret[akey] = cls.build_lte_predicate
            elif akey == 'gt':
                ret[akey] = cls.build_gt_predicate
            elif akey == 'gte':
                ret[akey] = cls.build_gte_predicate

        return ret

    @staticmethod
    def build_match_predicate(field, value):
        kwargs = { '{}__date'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_not_predicate(field, value):
        kwargs = { '{}__date'.format(field) : value }
        return ~Q(**kwargs)

    @staticmethod
    def build_in_predicate(field, value):
        kwargs = { '{}__date__in'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_not_in_predicate(field, value):
        kwargs = { '{}__date__in'.format(field) : value }
        return ~Q(**kwargs)

    @staticmethod
    def build_lt_predicate(field, value):
        kwargs = { '{}__date__lt'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_lte_predicate(field, value):
        kwargs = { '{}__date__lte'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_gt_predicate(field, value):
        kwargs = { '{}__date__gt'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_gte_predicate(field, value):
        kwargs = { '{}__date__gte'.format(field) : value }
        return Q(**kwargs)

    @classproperty
    def search_fields_list(cls):
        search_fields_list = {}

        for field_name in cls.fields:
            for suffix, func in cls.suffixes.items():
                field_wsuffix = field_name

                if suffix != '':
                    field_wsuffix = '{}_{}'.format(field_name, suffix)

                search_fields_list[field_wsuffix] = {
                    'function': func,
                    'field': field_name
                }

        return search_fields_list

    @classmethod
    def filter_queryset(cls, filter_values, qs):
        import copy

        cfilter_values = copy.deepcopy(filter_values)
        qobj_dict = {
            'AND': [],
            'OR': []
        }

        # iterate operations (AND/OR) and its array of values
        for and_or_op, op_filter_list in cfilter_values.items():
            array_idx = 0

            # iterate through the array of dicts of the operation
            for op_filter_values in op_filter_list:

                # iterate through the fields and values in these dicts
                for filter_name, filter_value in op_filter_values.items():
                    if filter_name in cls.search_fields_list:
                        # extract values
                        func = cls.search_fields_list[filter_name]['function']
                        field_name = cls.search_fields_list[filter_name]['field']

                        # call function and add q object
                        qobj = func(field_name, filter_value)
                        qobj_dict[and_or_op].append(qobj)

                        # delete value from filter
                        del filter_values[and_or_op][array_idx][filter_name]

                array_idx = array_idx + 1

        # filter the queryset with the q objects
        # do AND
        qand = None
        for qobj in qobj_dict['AND']:
            if not qand:
                qand = qobj
            else:
                qand = qand & qobj

        if qand:
            qs = qs.filter(qand)

        # do OR
        qor = None
        for qobj in qobj_dict['OR']:
            if not qor:
                qor = qobj
            else:
                qor = qor & qobj
        if qor:
            qs = qs.filter(qor)

        return qs

class UserQueryBuilder(DateQueryBuilder):
    fields = [ 'creator', 'modifier']

    @staticmethod
    def build_match_predicate(field, value):
        kwargs = { '{}'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_not_predicate(field, value):
        kwargs = { '{}'.format(field) : value }
        return ~Q(**kwargs)

    @staticmethod
    def build_in_predicate(field, value):
        kwargs = { '{}__in'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_not_in_predicate(field, value):
        kwargs = { '{}__in'.format(field) : value }
        return ~Q(**kwargs)

    @staticmethod
    def build_lt_predicate(field, value):
        kwargs = { '{}__lt'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_lte_predicate(field, value):
        kwargs = { '{}__lte'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_gt_predicate(field, value):
        kwargs = { '{}__gt'.format(field) : value }
        return Q(**kwargs)

    @staticmethod
    def build_gte_predicate(field, value):
        kwargs = { '{}__gte'.format(field) : value }
        return Q(**kwargs)

########## END CONNECTION FILTER BUILD FUNCTIONS

########## KEYVALUE TYPES
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
        ret.append(DictEntryType(name=key, value=value))

    return ret

########## END KEYVALUE TYPES

########## BASIC NI FIELDS
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

class NIChoiceField(NIBasicField):
    '''
    Choice type
    '''
    def __init__(self, field_type=ChoiceScalar, manual_resolver=False,
                    type_kwargs=None, **kwargs):
        super(NIChoiceField, self).__init__(field_type, manual_resolver,
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

########## END BASIC NI FIELDS


########## RELATION AND NODE TYPES
class User(DjangoObjectType):
    '''
    The django user type
    '''
    class Meta:
        model = DjangoUser
        only_fields = ['id', 'username', 'first_name', 'last_name']

class UserInputType(graphene.InputObjectType):
    username = graphene.String(required=True)

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

    def resolve_start_node(self, info, **kwargs):
        return NodeHandle.objects.get(handle_id=self.start['handle_id'])

    def resolve_end_node(self, info, **kwargs):
        return NodeHandle.objects.get(handle_id=self.end['handle_id'])

    @classmethod
    def get_filter_input_fields(cls):
        '''
        Method used by build_filter_and_order for a Relatio type
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
    class Meta:
        model = Comment

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
    comments = graphene.List(CommentType)

    def resolve_incoming(self, info, **kwargs):
        '''
        Resolver for incoming relationships for the node
        '''
        incoming_rels = self.get_node().incoming
        ret = []
        for rel_name, rel_list in incoming_rels.items():
            for rel in rel_list:
                relation_id = rel['relationship_id']
                rel = nc.get_relationship_model(nc.graphdb.manager, relationship_id=relation_id)
                ret.append(DictRelationType(name=rel_name, relation=rel))

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
                    for a, b in field_of_type.get_filter_input_fields().items():
                        filter_attrib[a] = b()

                    filter_attrib['_of_type'] = field._of_type

                    binput_field = type('{}InputField'.format(name_fot), (graphene.InputObjectType, ), filter_attrib)
                    input_fields[name] = binput_field, field._of_type

        input_fields['handle_id'] = graphene.Int

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
        ni_type = cls.get_from_nimetatype('ni_type')

        # build filter input class and order enum
        filter_attrib = {}
        cls.filter_names = {}
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

                # adding order attributes (only for scalar fields)
                enum_options.append(['{}_ASC'.format(field_name), '{}_ASC'.format(field_name)])
                enum_options.append(['{}_DESC'.format(field_name), '{}_DESC'.format(field_name)])
            else: # it must be a list other_node
                field_instance = input_field[0]()
                the_field = input_field[0]

            # adding filter attributes
            for suffix, suffix_attr in AbstractQueryBuilder.filter_array.items():
                # filter field naming
                if not suffix == '':
                    suffix = '_{}'.format(suffix)

                fmt_filter_field = '{}{}'.format(field_name, suffix)

                if not suffix_attr['only_strings'] \
                    or isinstance(field_instance, graphene.String):
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
                    try:
                        int_id = str(handle_id)
                        ret = NodeHandle.objects.filter(node_type=node_type).get(handle_id=int_id)
                    except ValueError:
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
                qs = NodeHandle.objects.all()

                if filter:
                    # filter queryset with dates and users
                    qs = DateQueryBuilder.filter_queryset(filter, qs)
                    qs = UserQueryBuilder.filter_queryset(filter, qs)

                    # create query
                    q = cls.build_filter_query(filter, type_name)
                    nodes = nc.query_to_list(nc.graphdb.manager, q)
                    nodes = [ node['n'].properties for node in nodes]
                else:
                    nodes = nc.get_nodes_by_type(nc.graphdb.manager, type_name)
                    nodes = list(nodes)

                if nodes:
                    handle_ids = []
                    qs_order_prop = None
                    qs_order_order = None

                    # ordering
                    if orderBy:
                        # extract field and order
                        m = re.match(r"([\w|\_]*)_(ASC|DESC)", orderBy)
                        prop = m[1]
                        order = m[2]

                        if prop not in DateQueryBuilder.fields:
                            # node property ordering
                            reverse = True if order == 'DESC' else False
                            nodes.sort(key=lambda x: x.get(prop, ''), reverse=reverse)
                        else: # set model attribute ordering
                            qs_order_prop  = prop
                            qs_order_order = order

                        handle_ids = [ node['handle_id'] for node in nodes ]
                    else:
                        handle_ids = [ node['handle_id'] for node in nodes ]
                        node_type = NodeType.objects.get(type=type_name)

                    ret = []

                    for handle_id in handle_ids:
                        nodeqs = qs.filter(handle_id=handle_id)
                        if nodeqs and len(nodeqs) == 1:
                            ret.append(nodeqs.first())

                    # do nodehandler attributes ordering now that we have
                    # the nodes set, if this order is requested
                    if qs_order_prop and qs_order_order:
                        reverse = True if qs_order_order == 'DESC' else False
                        ret.sort(key=lambda x: getattr(x, qs_order_prop, ''), reverse=reverse)

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

        # build OR block
        or_filters = filter.get('OR', [])
        or_predicates = []

        # additional clauses
        match_additional_nodes = []
        match_additional_rels  = []

        and_node_predicates = []
        and_rels_predicates = []

        # embed entity index
        idxdict = {
            'rel_idx': 1,
            'node_idx': 1,
            'subnode_idx': 1,
            'subrel_idx': 1,
        }

        operations = {
            'AND': {
                'filters': filter.get('AND', []),
                'predicates': [],
            },
            'OR': {
                'filters': filter.get('OR', []),
                'predicates': [],
            },
        }

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
                            # format var name and additional match
                            if issubclass(of_type, NIObjectType):
                                neo4j_var = '{}{}'.format(of_type.neo4j_var_name, idxdict['node_idx'])
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
                    else:
                        filter_array = ScalarQueryBuilder.filter_array
                        queryBuilder = ScalarQueryBuilder

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
                            build_predicate_func = fa_value['qpredicate']

                            predicate = build_predicate_func(field, filter_value, field_type, neo4j_var=neo4j_var)

                            if predicate:
                                predicates.append(predicate)

            operations[operation]['predicates'] = predicates

        and_query = ' AND '.join(operations['AND']['predicates'])
        or_query = ' OR '.join(operations['OR']['predicates'])

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

        # remove redundant additional clauses
        match_additional_nodes = list(set(match_additional_nodes))
        match_additional_rels = list(set(match_additional_rels))

        # prepare match clause
        node_match_clause = "(n:{label})".format(label=nodetype)
        additional_match_str = ', '.join( match_additional_nodes + match_additional_rels)

        if additional_match_str:
            node_match_clause = '{}, {}'.format(node_match_clause, additional_match_str)

        q = """
            MATCH {node_match_clause}
            {build_query}
            RETURN distinct n
            """.format(node_match_clause=node_match_clause, build_query=build_query)

        return q

    @classproperty
    def match_additional_clause(cls):
        return "({})-[{}]-({}{}:{})".format('{}', '{}', cls.neo4j_var_name, '{}',
                                        cls.NIMetaType.ni_type)

    neo4j_var_name = "m"

    class Meta:
        model = NodeHandle
        interfaces = (relay.Node, )

## add start and end fields
setattr(NIRelationType, 'start_node', graphene.Field(NIObjectType))
setattr(NIRelationType, 'end_node', graphene.Field(NIObjectType))
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
                graphene_field = ChoiceScalar(**graph_kwargs)
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
        has_error, ret = cls.do_request(reqinput[0], **reqinput[1])

        graphql_type = cls.get_graphql_type()
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
        has_error      = False

        ## code from role creation
        form = form_class(request.POST)
        if form.is_valid():
            try:
                nh = helpers.form_to_unique_node_handle(request, form,
                        node_type, node_meta_type)
            except UniqueNodeError:
                has_error = True
                return has_error, [ErrorType(field="_", messages=["A {} with that name already exists.".format(node_type)])]

            helpers.form_update_node(request.user, nh.handle_id, form)

            # process relations if implemented
            if not has_error:
                cls.process_relations(request, form, nh.get_node())

            return has_error, { graphql_type.__name__.lower(): nh }
        else:
            # get the errors and return them
            has_error = True
            errordict = cls.format_error_array(form.errors)
            return has_error, errordict

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
        has_error      = False

        nh, nodehandler = helpers.get_nh_node(handle_id)
        if request.POST:
            form = form_class(request.POST)
            if form.is_valid():
                # Generic node update
                helpers.form_update_node(request.user, nodehandler.handle_id, form)

                # process relations if implemented
                cls.process_relations(request, form, nodehandler)

                return has_error, { graphql_type.__name__.lower(): nh }
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
    class NIMetaClass:
        request_path   = None
        graphql_type   = None

    @classmethod
    def add_return_type(cls, graphql_type):
        setattr(cls, 'success', graphene.Boolean(required=True))

    @classmethod
    def do_request(cls, request, **kwargs):
        handle_id = request.POST.get('handle_id')

        nh, node = helpers.get_nh_node(handle_id)
        success = helpers.delete_node(request.user, node.handle_id)

        return not success, {'success': success}

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
        class_name = 'Create{}'.format(node_type.capitalize())
        attr_dict = {
            'django_form': create_form,
            'request_path': request_path,
            'is_create': True,
            'graphql_type': graphql_type,
            'include': create_include,
            'exclude': create_exclude,
        }

        if relations_processors:
            attr_dict['relations_processors'] = relations_processors

        create_metaclass = type(metaclass_name, (object,), attr_dict)

        cls._create_mutation = type(
            class_name,
            (cls.create_mutation_class,),
            {
                metaclass_name: create_metaclass,
            },
        )

        class_name = 'Update{}'.format(node_type.capitalize())
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

        class_name = 'Delete{}'.format(node_type.capitalize())
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

########## END MUTATION FACTORY

########## EXCEPTION AND AUTOQUERY
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

            if node_type:
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
########## END EXCEPTION AND AUTOQUERY
