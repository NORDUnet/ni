# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.tests.stressload.data_generator import FakeDataGenerator,\
                                                        NetworkFakeDataGenerator
from apps.noclook.models import NodeHandle, Dropdown
from collections import OrderedDict
from graphene import relay
from niweb.schema import schema
from pprint import pformat
from . import Neo4jGraphQLNetworkTest

import random

class GenericNetworkMutationTest(Neo4jGraphQLNetworkTest):
    def assert_failure(self, result, create_mutation):
        assert result.data[create_mutation]['errors'],\
            pformat(result.data[create_mutation]['errors'], indent=1)

    def create_mutation(self, create_mutation=None, entityname=None, data=None,
                        correct=True, generated_data=True):
        if not create_mutation or not entityname or not data:
            raise Exception('Missconfigured test {}'.format(type(self)))

        input_str = None
        inputs = []
        attrs = []
        values = {}
        node_data_test = {}

        input_tmpl = '{data_name}: "{data_f}",'

        for data_name, data_f in data.items():
            data_f_val = data_f
            subinput_str = None
            attr_str = None

            try:
                # throw the exception if isn't a dict
                data_f.items()

                if generated_data:
                    data_f_val = data_f['name']()
                else:
                    data_f_val = data_f['name']

                node_data_test[data_name] = data_f_val

                subinput_str = input_tmpl.format(
                    data_name=data_name,
                    data_f=data_f_val
                )

                attr_str = '{}{{\n\tname\n\tvalue \n}}'.format(data_name)

                values[data_name] = {}

                for k, v in data_f.items():
                    val = v
                    if generated_data:
                        val = v()

                    values[data_name][k] = val

            except AttributeError:
                if generated_data:
                    data_f_val = data_f()

                node_data_test[data_name] = data_f_val

                subinput_str = input_tmpl.format(
                    data_name=data_name,
                    data_f=data_f_val
                )
                values[data_name] = data_f_val
                attr_str = data_name

            if subinput_str:
                inputs.append(subinput_str)

            if attr_str:
                attrs.append(attr_str)

        values['id'] = None

        input_str = "\n".join(inputs)
        query_attr = "\n".join(attrs)

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

        if correct:
            assert not result.errors, pformat(result.errors, indent=1)

            id_str = result.data[create_mutation][entityname]['id']
            values['id'] = id_str

            expected = OrderedDict([(create_mutation,
                {
                    entityname: values,
                    'errors': None
                }
            )])

            self.assert_correct(result, expected)

            # check node creation
            values.pop('id', None)
            handle_id = relay.Node.from_global_id(id_str)[1]
            nh = NodeHandle.objects.get(handle_id=handle_id)
            self.assertDictContainsSubset(node_data_test, nh.get_node().data)

            return id_str
        else:
            self.assert_failure(result, create_mutation)

    def edit_mutation(self, update_mutation=None, entityname=None, id_str=None, data=None):
        if not update_mutation or not entityname or not data:
            raise Exception('Missconfigured test {}'.format(type(self)))

        input_str = None
        inputs = []
        attrs = []
        values = {}
        node_data_test = {}

        input_tmpl = '{data_name}: "{data_f}",'

        for data_name, data_f in data.items():
            data_f_val = data_f
            subinput_str = None
            attr_str = None

            try:
                # throw the exception if isn't a dict
                data_f.items()
                data_f_val = data_f['name']()
                node_data_test[data_name] = data_f_val

                subinput_str = input_tmpl.format(
                    data_name=data_name,
                    data_f=data_f_val
                )

                attr_str = '{}{{\n\tname\n\tvalue \n}}'.format(data_name)

                values[data_name] = {}

                for k, v in data_f.items():
                    values[data_name][k] = v()

            except AttributeError:
                data_f_val = data_f()
                node_data_test[data_name] = data_f_val

                subinput_str = input_tmpl.format(
                    data_name=data_name,
                    data_f=data_f_val
                )
                values[data_name] = data_f_val
                attr_str = data_name

            if subinput_str:
                inputs.append(subinput_str)

            if attr_str:
                attrs.append(attr_str)

        values['id'] = id_str

        input_str = "\n".join(inputs)
        query_attr = "\n".join(attrs)

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

        self.assert_correct(result, expected)

        # check node creation
        values.pop('id', None)
        handle_id = relay.Node.from_global_id(id_str)[1]
        nh = NodeHandle.objects.get(handle_id=handle_id)
        self.assertDictContainsSubset(node_data_test, nh.get_node().data)

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

    def crud(self, create_mutation=None, update_mutation=None,
                delete_mutation=None, entityname=None):
        if not create_mutation or not update_mutation or not delete_mutation\
            or not entityname:
            raise Exception('Missconfigured test {}'.format(type(self)))

        id_str = self.create_mutation(
            create_mutation=create_mutation,
            entityname=entityname
        )

        id_str = self.edit_mutation(
            id_str=id_str,
            update_mutation=update_mutation,
            entityname=entityname
        )

        success = self.delete_mutation(
            id_str=id_str,
            delete_mutation=delete_mutation
        )

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

    def unique_mutation(self, create_mutation=None, entityname=None):
        # this part should work
        data_generator = FakeDataGenerator()
        data = {
            'name': data_generator.rand_person_or_company_name(),
            'url': data_generator.fake.url(),
            'description': data_generator.fake.paragraph(),
        }

        id = GenericNetworkMutationTest.create_mutation(
            self,
            create_mutation=create_mutation,
            entityname=entityname,
            data=data,
            correct=True,
            generated_data=False
        )

        # this part should fail
        GenericNetworkMutationTest.create_mutation(
            self,
            create_mutation=create_mutation,
            entityname=entityname,
            data=data,
            correct=False,
            generated_data=False
        )

    def crud(self, create_mutation=None, update_mutation=None,
                delete_mutation=None, entityname=None):
        # test simple crud
        super().crud(
            create_mutation=create_mutation,
            update_mutation=update_mutation,
            delete_mutation=delete_mutation,
            entityname=entityname
        )

        # test unique_mutation
        self.unique_mutation(
            create_mutation=create_mutation,
            entityname=entityname
        )


class CustomerTest(GenericOrganizationTest):
    def test_crud(self):
        self.crud(
            create_mutation='create_customer',
            update_mutation='update_customer',
            delete_mutation='delete_customer',
            entityname='customer'
        )


class EndUserTest(GenericOrganizationTest):
    def test_crud(self):
        self.crud(
            create_mutation='create_endUser',
            update_mutation='update_endUser',
            delete_mutation='delete_endUser',
            entityname='endUser'
        )


class ProviderTest(GenericOrganizationTest):
    def test_crud(self):
        self.crud(
            create_mutation='create_provider',
            update_mutation='update_provider',
            delete_mutation='delete_provider',
            entityname='provider'
        )


class SiteOwnerTest(GenericOrganizationTest):
    def test_crud(self):
        self.crud(
            create_mutation='create_siteOwner',
            update_mutation='update_siteOwner',
            delete_mutation='delete_siteOwner',
            entityname='siteOwner'
        )

## Equipment and cables
class PortTest(GenericNetworkMutationTest):
    def create_mutation(self, create_mutation=None, entityname=None):
        data_generator = NetworkFakeDataGenerator()
        port_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:]
        )
        port_type_name  = lambda: port_type[0]
        port_type_value = lambda: port_type[1]

        data = {
            'name': data_generator.get_port_name,
            'port_type': {
                'name': port_type_name,
                'value': port_type_value,
            },
            'description': data_generator.fake.paragraph,
        }

        return super().create_mutation(
            create_mutation=create_mutation,
            entityname=entityname,
            data=data
        )

    def edit_mutation(self, update_mutation=None, entityname=None, id_str=None):
        data_generator = NetworkFakeDataGenerator()
        port_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:]
        )
        port_type_name  = lambda: port_type[0]
        port_type_value = lambda: port_type[1]

        data = {
            'name': data_generator.rand_person_or_company_name,
            'port_type': {
                'name': port_type_name,
                'value': port_type_value,
            },
            'description': data_generator.fake.paragraph,
        }

        return super().edit_mutation(
            update_mutation=update_mutation,
            entityname=entityname,
            id_str=id_str,
            data=data
        )

    def test_crud(self):
        self.crud(
            create_mutation='create_port',
            update_mutation='update_port',
            delete_mutation='delete_port',
            entityname='port'
        )
