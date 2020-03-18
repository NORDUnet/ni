# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.stressload.data_generator import FakeDataGenerator
from apps.noclook.models import NodeHandle
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLNetworkTest

class GenericNetworkMutationTest(Neo4jGraphQLNetworkTest):
    def create_mutation(self, create_mutation=None, entityname=None, data=None):
        if not create_mutation or not entityname or not data:
            raise Exception('Missconfigured test {}'.format(type(self)))

        input_str = None
        inputs = []
        values = {}

        for data_name, data_f in data.items():
            data_f_val = data_f()

            inputs.append('{data_name}: "{data_f}",'.format(
                data_name=data_name,
                data_f=data_f_val
            ))
            values[data_name] = data_f_val

        values['id'] = None

        input_str = "\n".join(inputs)
        query_attr = "\n".join(data.keys())

        ## create
        query = """
        mutation{{
          {create_mutation}(input:{{
            {input_str}
          }}){{
            errors{{
              field
              messages
            }}
            {entityname}{{
              id
              {query_attr}
            }}
          }}
        }}
        """.format(create_mutation=create_mutation, input_str=input_str,
                    query_attr=query_attr, entityname=entityname)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        id_str = result.data[create_mutation][entityname]['id']
        values['id'] = id_str

        expected = OrderedDict([(create_mutation,
            {
                entityname: values,
                'errors': None
            }
        )])

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        # check node creation
        values.pop('id', None)
        handle_id = relay.Node.from_global_id(id_str)[1]
        nh = NodeHandle.objects.get(handle_id=handle_id)
        self.assertDictContainsSubset(values, nh.get_node().data)

        return id_str


    def delete(self, delete_mutation=None, id_str=None):
        if not delete_mutation or not id_str:
            raise Exception('Missconfigured test {}'.format(type(self)))

        ## delete
        query = """
        mutation{{
          {delete_mutation}(input:{{
            id: "{id_str}"
          }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        """.format(delete_mutation=delete_mutation, id_str=id_str)

        expected = OrderedDict([(delete_mutation,
                    {
                        'success': True,
                        'errors': None
                    }
                )])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        # check node delete
        handle_id = relay.Node.from_global_id(id_str)[1]
        exists = NodeHandle.objects.filter(handle_id=handle_id).exists()
        self.assertFalse(exists)

        return result.data[delete_mutation]['success']

## Organizations
class GenericOrganizationTest(GenericNetworkMutationTest):
    def create_mutation(self, create_mutation=None, entityname=None):
        data_generator = FakeDataGenerator()
        data = {
            'name': data_generator.rand_person_or_company_name,
            'url': data_generator.fake.url,
            'description': data_generator.fake.paragraph,
        }

        return super().create_mutation(
            create_mutation=create_mutation,
            entityname=entityname,
            data=data
        )

    def edit(self, update_mutation=None, entityname=None, id_str=None):
        if not update_mutation or not entityname or not id_str:
            raise Exception('Missconfigured test {}'.format(type(self)))

        data_generator = FakeDataGenerator()
        the_name = data_generator.rand_person_or_company_name()
        the_url = data_generator.fake.url()
        the_description = data_generator.fake.paragraph()

        ## update
        query = """
        mutation{{
          {update_mutation}(input:{{
            id: "{id_str}"
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
        """.format(update_mutation=update_mutation, id_str=id_str,
                    the_name=the_name, the_url=the_url,
                    the_description=the_description, entityname=entityname)

        expected = OrderedDict([(update_mutation,
                    {
                        entityname: {
                            'id': id_str,
                            'name': the_name,
                            'url': the_url,
                            'description': the_description,
                        },
                        'errors': None
                    }
                )])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        # check node update
        handle_id = relay.Node.from_global_id(id_str)[1]
        nh = NodeHandle.objects.get(handle_id=handle_id)
        test_data = {
            'name': the_name,
            'url': the_url,
            'description': the_description,
        }
        self.assertDictContainsSubset(test_data, nh.get_node().data)

        return id_str

    def delete(self, delete_mutation=None, id_str=None):
        if not delete_mutation or not id_str:
            raise Exception('Missconfigured test {}'.format(type(self)))

        ## delete
        query = """
        mutation{{
          {delete_mutation}(input:{{
            id: "{id_str}"
          }}){{
            errors{{
              field
              messages
            }}
            success
          }}
        }}
        """.format(delete_mutation=delete_mutation, id_str=id_str)

        expected = OrderedDict([(delete_mutation,
                    {
                        'success': True,
                        'errors': None
                    }
                )])

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        assert result.data == expected, '{} \n != {}'.format(
                                                pformat(result.data, indent=1),
                                                pformat(expected, indent=1)
                                            )

        # check node delete
        handle_id = relay.Node.from_global_id(id_str)[1]
        exists = NodeHandle.objects.filter(handle_id=handle_id).exists()
        self.assertFalse(exists)

        return result.data[delete_mutation]['success']

class CustomerTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_customer',
            entityname='customer'
        )

        id_str = self.edit(
            id_str=id_str,
            update_mutation='update_customer',
            entityname='customer'
        )

        success = self.delete(
            id_str=id_str,
            delete_mutation='delete_customer'
        )


class EndUserTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_enduser',
            entityname='enduser'
        )

        id_str = self.edit(
            id_str=id_str,
            update_mutation='update_enduser',
            entityname='enduser'
        )

        success = self.delete(
            id_str=id_str,
            delete_mutation='delete_enduser'
        )


class ProviderTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_provider',
            entityname='provider'
        )

        id_str = self.edit(
            id_str=id_str,
            update_mutation='update_provider',
            entityname='provider'
        )

        success = self.delete(
            id_str=id_str,
            delete_mutation='delete_provider'
        )


class SiteOwnerTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_siteowner',
            entityname='siteowner'
        )

        id_str = self.edit(
            id_str=id_str,
            update_mutation='update_siteowner',
            entityname='siteowner'
        )

        success = self.delete(
            id_str=id_str,
            delete_mutation='delete_siteowner'
        )
