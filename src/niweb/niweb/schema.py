import graphene
import apps.noclook.schema as ncschema

class Query(ncschema.Query, graphene.ObjectType):
    pass

schema = graphene.Schema(
            query=Query,
            auto_camelcase=False,
        )
