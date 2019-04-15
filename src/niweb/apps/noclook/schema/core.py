# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import graphene
import re
from collections import OrderedDict
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions

from ..models import *

def get_srifield_resolver(field_name, field_type, rel_name=None, rel_method=None):
    def resolve_node_string(self, info, **kwargs):
        return self.get_node().data.get(field_name)

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

    if isinstance(field_type, graphene.String) or isinstance(field_type, graphene.Int):
        return resolve_node_string
    elif isinstance(field_type, graphene.List):
        return resolve_relationship_list
    else:
        return resolve_node_string

# define new and different types: String, List
class NIObjectField():
    def __init__(self, field_type=graphene.String, manual_resolver=False,
                    type_args=None, type_kwargs=None, rel_name=None,
                    rel_method=None, not_null_list=False, **kwargs):

        self.field_type      = field_type
        self.manual_resolver = manual_resolver
        self.type_args       = type_args
        self.type_kwargs     = type_kwargs
        self.rel_name        = rel_name
        self.rel_method      = rel_method
        self.not_null_list   = not_null_list

class NIObjectType(DjangoObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        sri_fields=None,
        **options,
    ):
        fields_names = ''
        allfields = cls.__dict__
        graphfields = OrderedDict()

        # getting all not magic attributes
        for name, field in allfields.items():
            pattern = re.compile("^__.*__$")
            if pattern.match(name) or callable(field):
                continue
            graphfields[name] = field

        # run over the fields defined and adding graphene fields and resolvers
        for name, field in graphfields.items():
            fields_names = fields_names + ' ' + '({} / {})'.format(name, field.__dict__)
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
                        get_srifield_resolver(
                            name,
                            field_value,
                            rel_name,
                            rel_method,
                        )
                )
            elif callable(manual_resolver):
                setattr(cls, 'resolve_{}'.format(name), manual_resolver)
            else:
                raise Exception(
                    'NIObjectField manual_resolver must be a callable in field {}'\
                        .format(name)
                )

        # add data field and resolver

        super(NIObjectType, cls).__init_subclass_with_meta__(
            model=NIObjectType._meta.model,
            **options
        )

    class Meta:
        model = NodeHandle
