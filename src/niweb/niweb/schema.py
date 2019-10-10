import graphene
import graphql_jwt
from apps.noclook.schema import NOCSCHEMA_QUERIES, NOCSCHEMA_MUTATIONS,\
                                    NOCSCHEMA_TYPES

ALL_TYPES = NOCSCHEMA_TYPES # + OTHER_APP_TYPES
ALL_QUERIES = NOCSCHEMA_QUERIES
ALL_MUTATIONS = NOCSCHEMA_MUTATIONS

class Query(*ALL_QUERIES, graphene.ObjectType):
    pass

class Mutation(*ALL_MUTATIONS, graphene.ObjectType):
    token_auth = graphql_jwt.relay.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.relay.Verify.Field()
    refresh_token = graphql_jwt.relay.Refresh.Field()
    #revoke_token = graphql_jwt.relay.Revoke.Field()

schema = graphene.Schema(
            query=Query,
            mutation=Mutation,
            auto_camelcase=False,
            types=ALL_TYPES
        )
