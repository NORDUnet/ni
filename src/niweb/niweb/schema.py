import graphene
from apps.noclook.schema import NOCSCHEMA_QUERIES, NOCSCHEMA_TYPES, NIRelayNode

class Query(*NOCSCHEMA_QUERIES, graphene.ObjectType):
    pass

ALL_TYPES = NOCSCHEMA_TYPES

schema = graphene.Schema(
            query=Query,
            auto_camelcase=False,
            types=ALL_TYPES
        )
