# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from collections import OrderedDict
from django.db.models import Q
from django.utils import six

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
        expression = """n.{field} = {value}"""
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)
            expression = """toLower(n.{field}) = toLower({value})"""

        ret = expression.format(field=field, value=value)

        return ret

    @staticmethod
    def build_not_predicate(field, value, type, **kwargs):
        # string quoting
        expression = """n.{field} <> {value}"""
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)
            expression = """toLower(n.{field}) <> toLower({value})"""

        ret = expression.format(field=field, value=value)

        return ret

    @staticmethod
    def build_in_predicate(field, values, type, **kwargs): # a list predicate builder
        expression = 'n.{field} IN [{list_string}]'
        value_list = []
        string_values = False
        for value in values:
            if isinstance(value, six.string_types):
                value = "toLower('{}')".format(value)
                string_values = True

            value_list.append(value)

        list_string = '{}'.format(', '.join(value_list))
        if string_values:
            expression = 'toLower(n.{field}) IN [{list_string}]'

        ret = expression.format(field=field, list_string=list_string)
        return ret

    @staticmethod
    def build_not_in_predicate(field, values, type, **kwargs): # a list predicate builder
        expression = 'NOT n.{field} IN [{list_string}]'
        value_list = []
        string_values = False
        for value in values:
            if isinstance(value, six.string_types):
                value = "toLower('{}')".format(value)
                string_values = True

            value_list.append(value)

        list_string = '{}'.format(', '.join(value_list))
        if string_values:
            expression = 'NOT toLower(n.{field}) IN [{list_string}]'

        ret = expression.format(field=field, list_string=list_string)
        return ret

    @staticmethod
    def build_lt_predicate(field, value, type, **kwargs):
        expression = """n.{field} < {value}"""
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)
            expression = """toLower(n.{field}) < toLower({value})"""

        ret = expression.format(field=field, value=value)

        return ret

    @staticmethod
    def build_lte_predicate(field, value, type, **kwargs):
        expression = """n.{field} <= {value}"""
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)
            expression = """toLower(n.{field}) <= toLower({value})"""

        ret = expression.format(field=field, value=value)

        return ret

    @staticmethod
    def build_gt_predicate(field, value, type, **kwargs):
        expression = """n.{field} > {value}"""
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)
            expression = """toLower(n.{field}) > toLower({value})"""

        ret = expression.format(field=field, value=value)

        return ret

    @staticmethod
    def build_gte_predicate(field, value, type, **kwargs):
        expression = """n.{field} >= {value}"""
        # string quoting
        if isinstance(value, six.string_types):
            value = "'{}'".format(value)
            expression = """toLower(n.{field}) >= toLower({value})"""

        ret = expression.format(field=field, value=value)

        return ret

    @staticmethod
    def build_contains_predicate(field, value, type, **kwargs):
        expression = """toLower(n.{field}) CONTAINS toLower('{value}')"""
        return expression.format(field=field, value=value)

    @staticmethod
    def build_not_contains_predicate(field, value, type, **kwargs):
        expression = """NOT toLower(n.{field}) CONTAINS toLower('{value}')"""
        return expression.format(field=field, value=value)

    @staticmethod
    def build_starts_with_predicate(field, value, type, **kwargs):
        expression = """toLower(n.{field}) STARTS WITH toLower('{value}')"""
        return expression.format(field=field, value=value)

    @staticmethod
    def build_not_starts_with_predicate(field, value, type, **kwargs):
        expression = """NOT toLower(n.{field}) STARTS WITH toLower('{value}')"""
        return expression.format(field=field, value=value)

    @staticmethod
    def build_ends_with_predicate(field, value, type, **kwargs):
        expression = """toLower(n.{field}) ENDS WITH toLower('{value}')"""
        return expression.format(field=field, value=value)

    @staticmethod
    def build_not_ends_with_predicate(field, value, type, **kwargs):
        expression = """NOT toLower(n.{field}) ENDS WITH toLower('{value}')"""
        return expression.format(field=field, value=value)

class InputFieldQueryBuilder(AbstractQueryBuilder):
    standard_expression = """{neo4j_var}.{field} {op} {value}"""
    standard_insensitive_expression = """toLower({neo4j_var}.{field}) {op} {value}"""
    id_expression = """ID({neo4j_var}) {op} {value}"""

    @classmethod
    def format_expression(cls, key, value, neo4j_var, op, add_quotes=True, string_values=False):
        # string quoting
        is_string = False

        if isinstance(value, str) and add_quotes:
            value = "toLower('{}')".format(value)
            is_string = True

        if key is 'relation_id':
            ret = cls.id_expression.format(
                neo4j_var=neo4j_var,
                op=op,
                value=value,
            )
        else:
            expression = cls.standard_expression
            if is_string or string_values:
                expression = cls.standard_insensitive_expression

            ret = expression.format(
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

        string_filter = False
        all_values = []
        field_name = ""

        for value in values:
            for k, v in value.items():
                if isinstance(v, str):
                    v = "toLower('{}')".format(v)
                    string_filter = True

                field_name = k
                all_values.append(v)

        the_value = "[{}]".format(', '.join([str(x) for x in all_values]))

        ret = InputFieldQueryBuilder.format_expression(field_name, the_value, neo4j_var, op, False, string_filter)

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
