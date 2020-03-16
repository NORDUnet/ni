# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.stressload.data_generator import FakeDataGenerator
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLNetworkTest

## Organizations
class GenericOrganizationTest(Neo4jGraphQLNetworkTest):
    def create(self, create_mutation=None, entityname=None):
        if not create_mutation:
            raise Exception('Missconfigured test {}'.format(type(self)))

        data_generator = FakeDataGenerator()
        the_name = data_generator.rand_person_or_company_name()
        the_url = data_generator.fake.url()
        the_description = data_generator.fake.paragraph()

        ## create
        query = """
        mutation{{
          {create_mutation}(input:{{
            name: "{the_name}",
            url: "{the_url}",
            description: "{the_description}"
          }}){{
            errors{{
              field
              messages
            }}
            {entityname}{{
              id
              name
              url
              description
            }}
          }}
        }}
        """.format(create_mutation=create_mutation, the_name=the_name,
                    the_url=the_url, the_description=the_description,
                    entityname=entityname)

        expected = OrderedDict([('create_customer',
                    {
                        entityname: {
                            'id': None,
                            'name': the_name,
                            'url': the_url,
                            'description': the_description,
                        },
                        'errors': None
                    }
                )])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        id_str = result.data[create_mutation][entityname]['id']
        expected[create_mutation][entityname]['id'] = id_str

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        return id_str

class CustomerTest(GenericOrganizationTest):
    def test_crud(self):
        customer_id = self.create(
            create_mutation='create_customer',
            entityname='customer'
        )
