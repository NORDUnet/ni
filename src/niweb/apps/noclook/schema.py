import graphene
from graphene_django import DjangoObjectType

from .models import *

class NodeTypeType(DjangoObjectType):
    class Meta:
        model = NodeType

class NodeHandleType(DjangoObjectType):
    class Meta:
        model = NodeHandle

class RoleType(NodeHandleType):
    name = graphene.String(required=True)

    def resolve_name(self, info, **kwargs):
        return self.get_node().data['name']

    class Meta:
        model = NodeHandle

class Query(graphene.ObjectType):
    nodetypes = graphene.List(NodeTypeType)
    nodehandles = graphene.List(NodeHandleType)
    roles = graphene.List(RoleType)

    def resolve_nodetypes(self, info, **kwargs):
        return NodeType.objects.all()

    def resolve_nodehandles(self, info, **kwargs):
        return NodeHandle.objects.all()

    def resolve_roles(self, info, **kwargs):
        role_type = NodeType.objects.get(type="Role")
        return NodeHandle.objects.filter(node_type=role_type)
