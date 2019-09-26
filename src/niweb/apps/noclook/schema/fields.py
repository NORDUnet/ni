# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene

from apps.noclook.models import NodeHandle

from .scalars import ChoiceScalar

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
