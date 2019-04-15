import graphene
import apps.noclook.schema as nocschema

class Query(nocschema.Query, graphene.ObjectType):
    pass

schema = graphene.Schema(
            query=Query,
            auto_camelcase=False,
            types=[
                nocschema.RoleType,
                nocschema.ContactType,
            ]
        )
