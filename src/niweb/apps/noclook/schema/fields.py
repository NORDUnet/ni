# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, Choice as ChoiceModel, Dropdown as DropdownModel
from apps.noclook.vakt import utils as sriutils
from collections import OrderedDict
from graphene_django import DjangoObjectType
from .scalars import ChoiceScalar, IPAddr, JSON

import graphene
import types as pytypes
import warnings

########## KEYVALUE TYPES
class KeyValue(graphene.Interface):
    name = graphene.String(required=True)
    value = graphene.String(required=True)


class Choice(DjangoObjectType):
    '''
    This class is used for the choices available in a dropdown
    '''
    class Meta:
        model = ChoiceModel
        interfaces = (KeyValue, )


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

class NIBasicField():
    '''
    Super class of the type fields
    '''
    def __init__(self, field_type=graphene.String, manual_resolver=False,
                    type_kwargs=None, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_kwargs     = type_kwargs

    def get_default_value(self):
        # this will trigger a exception for fields that don't define this method
        return None

    def get_resolver(self, **kwargs):
        field_name = kwargs.get('field_name')
        if not field_name:
            raise Exception(
                'Field name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )
        def resolve_node_value(instance, info, **kwargs):
            node = self.get_inner_node(instance)
            value = node.data.get(field_name)
            is_required = False

            if self.type_kwargs and self.type_kwargs.get('required', False):
                is_required = True

            if value == None and is_required:
                value = self.get_default_value()

            return value

        return resolve_node_value

    def get_field_type(self):
        return self.field_type

    def get_inner_node(self, instance):
        if not hasattr(instance, '_node'):
            instance._node = instance.get_node()

        return instance._node

class NIStringField(NIBasicField):
    '''
    String type
    '''
    def get_default_value(self):
        return ''

class NIIntField(NIBasicField):
    '''
    Int type
    '''
    def __init__(self, field_type=graphene.Int, manual_resolver=False,
                    type_kwargs=None, **kwargs):
        super(NIIntField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)

    def get_default_value(self):
        return -1


class NIBooleanField(NIBasicField):
    '''
    Boolean type
    '''
    def __init__(self, field_type=graphene.Boolean, manual_resolver=False,
                    type_kwargs=None, **kwargs):
        super(NIBooleanField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)

    def get_default_value(self):
        return False

    def get_resolver(self, **kwargs):
        field_name = kwargs.get('field_name')
        if not field_name:
            raise Exception(
                'Field name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )
        def resolve_node_value(instance, info, **kwargs):
            possible_value = self.get_inner_node(instance).data.get(field_name)
            if possible_value == None:
                possible_value = self.get_default_value()

            return possible_value

        return resolve_node_value


class NIIPAddrField(NIBasicField):
    '''
    IPAddr type
    '''
    def __init__(self, field_type=IPAddr, manual_resolver=False,
                    type_kwargs=None, **kwargs):
        super(NIIPAddrField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)


class NIJSONField(NIBasicField):
    '''
    JSO type
    '''
    def __init__(self, field_type=JSON, manual_resolver=False,
                    type_kwargs=None, **kwargs):
        super(NIJSONField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)


class NISingleRelationField(NIBasicField):
    '''
    Object list type
    '''
    def __init__(self, field_type=None, manual_resolver=False, type_kwargs=None,
                    rel_method=None, rel_name=None, check_permissions=True, **kwargs):

        self.type_kwargs       = type_kwargs
        self.field_type        = lambda: graphene.Field(field_type)
        self.manual_resolver   = manual_resolver
        self.rel_method        = rel_method
        self.rel_name          = rel_name
        self.check_permissions = check_permissions

    def get_resolver(self, **kwargs):
        rel_method = kwargs.get('rel_method')
        rel_name = kwargs.get('rel_name')

        def resolve_relationship_object(instance, info, **kwargs):
            ret = None

            neo4jnode = self.get_inner_node(instance)
            relationship = getattr(neo4jnode, rel_method)()

            if relationship and rel_name in relationship:
                node = relationship[rel_name][0]
                relation_id = node['relationship_id']
                handle_id = node['node'].data['handle_id']

                authorized = False

                if sriutils.authorice_read_resource(info.context.user, handle_id):
                    authorized = True
                else:
                    authorized = not self.check_permissions

                if authorized:
                    ret = NodeHandle.objects.get(handle_id=handle_id)
                    # add relationship_id
                    ret.relation_id = relation_id

            return ret

        return resolve_relationship_object


class NIListField(NIBasicField):
    '''
    Object list type
    '''
    def __init__(self, field_type=graphene.List, manual_resolver=False,
                    type_args=None, rel_name=None, rel_method=None,
                    not_null_list=False, unique=False, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_args       = type_args
        self.rel_name        = rel_name
        self.rel_method      = rel_method
        self.not_null_list   = not_null_list
        self.unique          = unique

    def get_default_value(self):
        return []

    def get_resolver(self, **kwargs):
        rel_name   = kwargs.get('rel_name')
        rel_method = kwargs.get('rel_method')

        def resolve_relationship_list(instance, info, **kwargs):
            neo4jnode = self.get_inner_node(instance)
            relations = getattr(neo4jnode, rel_method)()
            nodes = relations.get(rel_name)

            id_list = []
            if nodes:
                for node in nodes:
                    relation_id = node['relationship_id']
                    node_elem = node['node']
                    node_id = node_elem.data.get('handle_id')

                    if not relation_id:
                        relation_id = -1
                        warnings.warn(
                            "relationship_id is None".format(node),
                            RuntimeWarning
                        )


                    id_list.append((node_id, relation_id))

            id_list = sorted(id_list, key=lambda x: x[0])

            ret = []
            for handle_id, relation_id in id_list:
                nh = NodeHandle.objects.get(handle_id=handle_id)
                nh.relation_id = relation_id

                if sriutils.authorice_read_resource(info.context.user, nh.handle_id):
                    ret.append(nh)

            # don't repeat objects on list
            if self.unique:
                ret = list(OrderedDict.fromkeys(ret))

            return ret

        return resolve_relationship_list


# convenience class
class ComplexField():
    pass


class NIChoiceField(NIBasicField, ComplexField):
    '''
    Choice type
    '''
    def __init__(self, field_type=Choice, manual_resolver=False,
                    dropdown_name=None, type_kwargs=None, **kwargs):
        self.dropdown_name = dropdown_name
        super(NIChoiceField, self).__init__(field_type, manual_resolver,
                        type_kwargs, **kwargs)

    def get_resolver(self, **kwargs):
        field_name = kwargs.get('field_name')

        if not field_name:
            raise Exception(
                'Field name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )

        dropdown_name = kwargs.get('dropdown_name')

        if not dropdown_name:
            raise Exception(
                'Dropdown name for field {} should not be empty for a {}'.format(
                    field_name, self.__class__
                )
            )

        def resolve_node_value(self, info, **kwargs):
            # resolve dropdown
            if DropdownModel.objects.filter(name=dropdown_name):
                dropdown = DropdownModel.objects.get(name=dropdown_name)

                # resolve choice
                node_value = self.get_node().data.get(field_name)
                choice_val = ChoiceModel.objects.filter(
                    dropdown=dropdown,
                    value=node_value
                ).first()

                return choice_val
            else:

                raise Exception('Not valid dropdown "{}\n Available choices are:\n{}"'.format(
                    dropdown_name,
                    ', '.join([x.name for x in DropdownModel.objects.all()])
                ))

        return resolve_node_value


class IDRelation(graphene.ObjectType):
    entity_id = graphene.ID()
    relation_id = graphene.Int()


def is_lambda_function(obj):
    return isinstance(obj, pytypes.LambdaType) and obj.__name__ == "<lambda>"


class NIRelationListField(NIBasicField):
    '''
    ID/relation_id list type
    '''
    def __init__(self, field_type=graphene.List, manual_resolver=False,
                    type_args=(IDRelation,), rel_name=None, rel_method=None,
                    not_null_list=False, graphene_type=None, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_args       = type_args
        self.rel_name        = rel_name
        self.rel_method      = rel_method
        self.not_null_list   = not_null_list
        self.graphene_type   = graphene_type

    def get_resolver(self, **kwargs):
        rel_name   = kwargs.get('rel_name')
        rel_method = kwargs.get('rel_method')
        graphene_type = self.graphene_type

        def resolve_relationship_list(instance, info, **kwargs):
            neo4jnode = self.get_inner_node(instance)
            relations = getattr(neo4jnode, rel_method)()
            nodes = relations.get(rel_name)

            if is_lambda_function(graphene_type):
                type_str = str(graphene_type())
            else:
                type_str = str(graphene_type)

            handle_id_list = []
            if nodes:
                for node in nodes:
                    relation_id = node['relationship_id']
                    node = node['node']
                    node_id = node.data.get('handle_id')
                    id = graphene.relay.Node.to_global_id(
                        type_str, str(node_id)
                    )
                    id_relation = IDRelation()
                    id_relation.entity_id = id
                    id_relation.relation_id = relation_id
                    handle_id_list.append(id_relation)

            return handle_id_list

        return resolve_relationship_list
