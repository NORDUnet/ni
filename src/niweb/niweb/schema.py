import graphene
from apps.noclook.schema import NOCSCHEMA_QUERIES, NOCSCHEMA_MUTATIONS,\
                                    NOCSCHEMA_TYPES, NIRelayNode

ALL_TYPES = NOCSCHEMA_TYPES # + OTHER_APP_TYPES
ALL_QUERIES = NOCSCHEMA_QUERIES
ALL_MUTATIONS = NOCSCHEMA_MUTATIONS

class Query(*ALL_QUERIES, graphene.ObjectType):
    pass

class Mutation(*ALL_MUTATIONS, graphene.ObjectType):
    pass

schema = graphene.Schema(
            query=Query,
            mutation=Mutation,
            auto_camelcase=False,
            types=ALL_TYPES
        )
