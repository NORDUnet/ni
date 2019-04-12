import graphene
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions

from .models import *

def get_srifield_resolver(field_name, field_type):
    def srifield_resolver(self, info, **kwargs):
        return self.get_node().data.get(field_name)

    if isinstance(field_type, graphene.String) or isinstance(field_type, graphene.Int):
        return srifield_resolver
    else:
        return srifield_resolver

class NIObjectType(DjangoObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        sri_fields=None,
        **options,
    ):
        if sri_fields:
            for sri_field, sri_dict in sri_fields.items():
                field_kwargs = sri_dict.get('kwargs', {})
                field_type = sri_dict['type']

                # adding the field
                setattr(cls, sri_field, field_type(**field_kwargs))

                # adding the resolver
                setattr(cls, 'resolve_{}'.format(sri_field), \
                        get_srifield_resolver(sri_field, field_type))

        super(NIObjectType, cls).__init_subclass_with_meta__(
            model=NodeHandle,
            **options
        )

    class Meta:
        model = NodeHandle

class RoleType(NIObjectType):
    class Meta:
        sri_fields = {
            'name': { 'type': graphene.String, 'kwargs': { 'required': True } },
        }

class ContactType(NIObjectType):
    is_roles = graphene.List(RoleType)

    def resolve_is_roles(self, info, **kwargs):
        relations = self.get_node().get_outgoing_relations()
        roles = relations.get('Is')

        # this may be the worst way to do it, but it's just for a PoC
        handle_id_list = []
        for role in roles:
            role = role['node']
            role_id = role.data.get('handle_id')
            handle_id_list.append(role_id)

        ret = NodeHandle.objects.filter(handle_id__in=handle_id_list)

        return ret

    class Meta:
        sri_fields = {
            'name': { 'type': graphene.String, 'kwargs': { 'required': True } },
            'first_name': { 'type': graphene.String, 'kwargs': { 'required': True } },
            'last_name': { 'type': graphene.String, 'kwargs': { 'required': True } },
            'title': { 'type': graphene.String },
            'salutation': { 'type': graphene.String },
            'contact_type': { 'type': graphene.String }, # enum
            'phone': { 'type': graphene.String },
            'mobile': { 'type': graphene.String },
            'email': { 'type': graphene.String },
            'other_email': { 'type': graphene.String },
            'PGP_fingerprint': { 'type': graphene.String },
        }

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
