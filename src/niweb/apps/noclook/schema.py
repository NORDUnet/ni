import graphene
import re
from collections import OrderedDict
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions

from .models import *

def get_srifield_resolver(field_name, field_type, rel_name='', rel_method=None):
    def srifield_resolver(self, info, **kwargs):
        return self.get_node().data.get(field_name)

    def resolve_is_roles(self, info, **kwargs):
        neo4jnode = self.get_node()
        relations = neo4jnode.getattr(rel_method)()
        roles = relations.get(rel_name)

        # this may be the worst way to do it, but it's just for a PoC
        handle_id_list = []
        for role in roles:
            role = role['node']
            role_id = role.data.get('handle_id')
            handle_id_list.append(role_id)

        ret = NodeHandle.objects.filter(handle_id__in=handle_id_list)

        return ret

    if isinstance(field_type, graphene.String) or isinstance(field_type, graphene.Int):
        return srifield_resolver
    elif isinstance(field_type, graphene.List):
        return resolve_is_roles
    else:
        return srifield_resolver

class NIObjectField():
    def __init__(self, field_type=graphene.String, type_args=None,
                    type_kwargs=None, rel_name=None, rel_method=None, **kwargs):
        self.field_type     = field_type
        self.type_args      = type_args
        self.type_kwargs    = type_kwargs
        self.rel_name       = rel_name
        self.rel_method     = rel_method

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
        for name, field in allfields.items():
            pattern = re.compile("^__.*__$")
            if pattern.match(name):# or callable(field):
                continue
            graphfields[name] = field

        for name, field in graphfields.items():
            fields_names = fields_names + ' ' + '({} / {})'.format(name, field.__dict__)
            field_fields = field.__dict__

            field_type = field_fields.get('field_type')
            type_kwargs = field_fields.get('type_kwargs')
            type_args = field_fields.get('type_args')
            rel_name = field_fields.get('rel_name')
            rel_method = field_fields.get('rel_method')

            # adding the field
            if type_kwargs:
                field_value = field_type(**type_kwargs)
            elif type_args:
                field_value = field_type(*type_args)
            else:
                field_value = field_type(**{})

            setattr(cls, name, field_value)

            # adding the resolver
            setattr(cls, 'resolve_{}'.format(name), \
                    get_srifield_resolver(
                        name,
                        field_type,
                        rel_name,
                        rel_method,
                    )
            )

        super(NIObjectType, cls).__init_subclass_with_meta__(
            model=NIObjectType._meta.model,
            **options
        )

    class Meta:
        model = NodeHandle

class RoleType(NIObjectType):
    name = NIObjectField(type_kwargs={ 'required': True })

class ContactType(NIObjectType):
    name = NIObjectField(type_kwargs={ 'required': True })
    first_name = NIObjectField(type_kwargs={ 'required': True })
    last_name = NIObjectField(type_kwargs={ 'required': True })
    title = NIObjectField()
    salutation = NIObjectField()
    contact_type = NIObjectField()
    phone = NIObjectField()
    mobile = NIObjectField()
    email = NIObjectField()
    other_email = NIObjectField()
    PGP_fingerprint = NIObjectField()
    is_roles = NIObjectField(field_type=graphene.List, type_args=(RoleType,), rel_name='Is', rel_method='get_outgoing_relations')

class Query(graphene.ObjectType):
    roles = graphene.List(RoleType, limit=graphene.Int())
    contacts = graphene.List(ContactType, limit=graphene.Int())

    def resolve_roles(self, info, **args):
        limit = args.get('limit', False)
        type = NodeType.objects.get(type="Role") # TODO too raw
        if limit:
            return NodeHandle.objects.filter(node_type=type)[:10]
        else:
            return NodeHandle.objects.filter(node_type=type)

    def resolve_contacts(self, info, **args):
        limit = args.get('limit', False)
        type = NodeType.objects.get(type="Contact") # TODO too raw
        if limit:
            return NodeHandle.objects.filter(node_type=type)[:10]
        else:
            return NodeHandle.objects.filter(node_type=type)
