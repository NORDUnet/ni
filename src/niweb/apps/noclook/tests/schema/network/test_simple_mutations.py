# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.stressload.data_generator import FakeDataGenerator
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLNetworkTest

## Organizations
class CustomerTest(Neo4jGraphQLNetworkTest):
    def test_crud(self):
        data_generator = FakeDataGenerator()
        customer_name = data_generator.rand_person_or_company_name()
        customer_url = data_generator.fake.url()
        customer_description = data_generator.fake.paragraph()

        ## create
        query = """
        mutation{{
          create_customer(input:{{
            name: "{customer_name}",
            url: "{customer_url}",
            description: "{customer_description}"
          }}){{
            errors{{
              field
              messages
            }}
            customer{{
              id
              name
              url
              description
            }}
          }}
        }}
        """.format(customer_name=customer_name, customer_url=customer_url,
                    customer_description=customer_description)

        expected = OrderedDict([('create_customer',
              {'customer': {'description': customer_description,
                            'id': None,
                            'name': customer_name,
                            'url': customer_url},
               'errors': None})])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        customer_id_str = result.data['create_customer']['customer']['id']
        expected['create_customer']['customer']['id'] = customer_id_str

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        ## edit
        customer_url = data_generator.fake.url()
        customer_description = data_generator.fake.paragraph()
