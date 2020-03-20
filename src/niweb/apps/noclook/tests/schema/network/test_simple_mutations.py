# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.stressload.data_generator import FakeDataGenerator,\
                                                        NetworkFakeDataGenerator
from apps.noclook.models import NodeHandle
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLNetworkTest

import random

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

    def edit_mutation(self, update_mutation=None, entityname=None, id_str=None, data=None):
        if not update_mutation or not entityname or not data:
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

        values['id'] = id_str

        input_str = "\n".join(inputs)
        query_attr = "\n".join(data.keys())

        ## create
        query = """
        mutation{{
          {update_mutation}(input:{{
            id: "{id_str}"
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
        """.format(update_mutation=update_mutation, id_str=id_str,
                    input_str=input_str, query_attr=query_attr,
                    entityname=entityname)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected = OrderedDict([(update_mutation,
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

    def delete_mutation(self, delete_mutation=None, id_str=None):
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

    def edit_mutation(self, update_mutation=None, entityname=None, id_str=None):
        data_generator = FakeDataGenerator()
        data = {
            'name': data_generator.rand_person_or_company_name,
            'url': data_generator.fake.url,
            'description': data_generator.fake.paragraph,
        }

        return super().edit_mutation(
            update_mutation=update_mutation,
            entityname=entityname,
            id_str=id_str,
            data=data
        )


class CustomerTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_customer',
            entityname='customer'
        )

        id_str = self.edit_mutation(
            id_str=id_str,
            update_mutation='update_customer',
            entityname='customer'
        )

        success = self.delete_mutation(
            id_str=id_str,
            delete_mutation='delete_customer'
        )


class EndUserTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_endUser',
            entityname='enduser'
        )

        id_str = self.edit_mutation(
            id_str=id_str,
            update_mutation='update_endUser',
            entityname='enduser'
        )

        success = self.delete_mutation(
            id_str=id_str,
            delete_mutation='delete_endUser'
        )


class ProviderTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_provider',
            entityname='provider'
        )

        id_str = self.edit_mutation(
            id_str=id_str,
            update_mutation='update_provider',
            entityname='provider'
        )

        success = self.delete_mutation(
            id_str=id_str,
            delete_mutation='delete_provider'
        )


class SiteOwnerTest(GenericOrganizationTest):
    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_siteOwner',
            entityname='siteowner'
        )

        id_str = self.edit_mutation(
            id_str=id_str,
            update_mutation='update_siteOwner',
            entityname='siteowner'
        )

        success = self.delete_mutation(
            id_str=id_str,
            delete_mutation='delete_siteOwner'
        )

## Equipment and cables
class PortTest(GenericNetworkMutationTest):
    def create_mutation(self, create_mutation=None, entityname=None):
        data_generator = NetworkFakeDataGenerator()
        port_types = data_generator.get_dropdown_keys('port_types')

        data = {
            'name': data_generator.get_port_name,
            'port_type': lambda: random.choice(port_types),
            'description': data_generator.fake.paragraph,
        }

        return super().create_mutation(
            create_mutation=create_mutation,
            entityname=entityname,
            data=data
        )

    def edit_mutation(self, update_mutation=None, entityname=None, id_str=None):
        data_generator = NetworkFakeDataGenerator()
        port_types = data_generator.get_dropdown_keys('port_types')

        data = {
            'name': data_generator.rand_person_or_company_name,
            'port_type': lambda: random.choice(port_types),
            'description': data_generator.fake.paragraph,
        }

        return super().edit_mutation(
            update_mutation=update_mutation,
            entityname=entityname,
            id_str=id_str,
            data=data
        )

    def test_crud(self):
        id_str = self.create_mutation(
            create_mutation='create_port',
            entityname='port'
        )

        id_str = self.edit_mutation(
            id_str=id_str,
            update_mutation='update_port',
            entityname='port'
        )

        success = self.delete_mutation(
            id_str=id_str,
            delete_mutation='delete_port'
        )
