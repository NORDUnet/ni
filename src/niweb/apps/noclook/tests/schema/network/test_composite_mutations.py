# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, Dropdown, Choice, Group, \
    GroupContextAuthzAction, NodeHandleContext, SwitchType
from apps.noclook.tests.stressload.data_generator \
    import NetworkFakeDataGenerator, CommunityFakeDataGenerator
from apps.noclook.schema.utils import sunet_forms_enabled
from collections import OrderedDict
from . import Neo4jGraphQLNetworkTest
from niweb.schema import schema
from pprint import pformat
from graphene import relay

import random

## Equipment and cables
class PortCompositeTest(Neo4jGraphQLNetworkTest):
    def test_composite_port(self):
        # Create query

        port_name = "test-01"
        port_type = "Schuko"
        port_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."

        cable_name = "Test cable"
        cable_type = "Patch"
        cable_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        pport_name = "test-00"
        pport_type = "Schuko"
        pport_description = "Nunc varius suscipit lorem, non posuere nisl "\
            "consequat in. Nulla gravida sapien a velit aliquet, aliquam "\
            "tincidunt urna ultrices. Vivamus venenatis ligula a erat "\
            "fringilla faucibus. Suspendisse potenti. Donec rutrum eget "\
            "nunc sed volutpat. Curabitur sit amet lorem elementum sapien "\
            "ornare placerat."

        query = '''
        mutation{{
          composite_port(input:{{
            create_input:{{
              name: "{port_name}"
              port_type: "{port_type}"
              description: "{port_description}"
            }}
            create_subinputs:[{{
              name: "{cable_name}"
              cable_type: "{cable_type}"
              description: "{cable_description}"
            }}]
            create_parent_port:[{{
              name: "{pport_name}"
              port_type: "{pport_type}"
              description: "{pport_description}"
            }}]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  value
                }}
                description
                parent{{
                  id
                  name
                  ...on Port{{
                    port_type{{
                      value
                    }}
                    description
                  }}
                }}
                connected_to{{
                  id
                  name
                  ...on Cable{{
                    description
                    cable_type{{
                      value
                    }}
                  }}
                }}
              }}
            }}
            subcreated{{
              errors{{
                field
                messages
              }}
              cable{{
                id
                name
                description
                cable_type{{
                  value
                }}
              }}
            }}
            parent_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  value
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(port_name=port_name, port_type=port_type,
            port_description=port_description, cable_name=cable_name,
            cable_type=cable_type, cable_description=cable_description,
            pport_name=pport_name, pport_type=pport_type,
            pport_description=pport_description)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_port']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_port']['subcreated']:
            assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

        for subcreated in result.data['composite_port']['parent_port_created']:
            assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)


        # get the ids
        result_data = result.data['composite_port']
        port_id = result_data['created']['port']['id']
        cable_id = result_data['subcreated'][0]['cable']['id']
        pport_id = result_data['parent_port_created'][0]['port']['id']

        # check the integrity of the data
        created_data = result_data['created']['port']

        # check main port
        self.assertEqual(created_data['name'], port_name)
        self.assertEqual(created_data['port_type']['value'], port_type)
        self.assertEqual(created_data['description'], port_description)

        # check their relations id
        test_cable_id = created_data['connected_to'][0]['id']
        test_pport_id = created_data['parent'][0]['id']

        self.assertEqual(cable_id, test_cable_id)
        self.assertEqual(pport_id, test_pport_id)

        # check cable in both payload and metatype attribute
        check_cables = [
            result_data['subcreated'][0]['cable'],
            created_data['connected_to'][0],
        ]

        for check_cable in check_cables:
            self.assertEqual(check_cable['name'], cable_name)
            self.assertEqual(check_cable['cable_type']['value'], cable_type)
            self.assertEqual(check_cable['description'], cable_description)

        # check parent port in payload and in metatype attribute
        created_parents = [
            result_data['parent_port_created'][0]['port'],
            created_data['parent'][0],
        ]

        for created_parent in created_parents:
            self.assertEqual(created_parent['name'], pport_name)
            self.assertEqual(created_parent['port_type']['value'], pport_type)
            self.assertEqual(created_parent['description'], pport_description)

        ## Update query
        buffer_description = port_description
        buffer_description2 = pport_description

        port_name = "rj45-01"
        port_type = "RJ45"
        port_description = cable_description

        cable_name = "Test cable"
        cable_type = "Patch"
        cable_description = buffer_description2

        pport_name = "lc-01"
        pport_type = "LC"
        pport_description = buffer_description

        query = '''
        mutation{{
          composite_port(input:{{
            update_input:{{
              id: "{port_id}"
              name: "{port_name}"
              port_type: "{port_type}"
              description: "{port_description}"
            }}
            update_subinputs:[{{
              id: "{cable_id}"
              name: "{cable_name}"
              cable_type: "{cable_type}"
              description: "{cable_description}"
            }}]
            update_parent_port:[{{
              id: "{pport_id}"
              name: "{pport_name}"
              port_type: "{pport_type}"
              description: "{pport_description}"
            }}]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  value
                }}
                description
                parent{{
                  id
                  name
                  ...on Port{{
                    port_type{{
                      value
                    }}
                    description
                  }}
                }}
                connected_to{{
                  id
                  name
                  ...on Cable{{
                    description
                    cable_type{{
                      value
                    }}
                  }}
                }}
              }}
            }}
            subupdated{{
              errors{{
                field
                messages
              }}
              cable{{
                id
                name
                description
                cable_type{{
                  value
                }}
              }}
            }}
            parent_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  value
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(port_id=port_id, port_name=port_name, port_type=port_type,
            port_description=port_description, cable_id=cable_id,
            cable_name=cable_name, cable_type=cable_type,
            cable_description=cable_description, pport_id=pport_id,
            pport_name=pport_name, pport_type=pport_type,
            pport_description=pport_description)


        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_port']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        for subupdated in result.data['composite_port']['subupdated']:
            assert not subupdated['errors'], pformat(subupdated['errors'], indent=1)

        for subupdated in result.data['composite_port']['parent_port_updated']:
            assert not subupdated['errors'], pformat(subupdated['errors'], indent=1)

        # check the integrity of the data
        result_data = result.data['composite_port']
        updated_data = result_data['updated']['port']

        # check main port
        self.assertEqual(updated_data['name'], port_name)
        self.assertEqual(updated_data['port_type']['value'], port_type)
        self.assertEqual(updated_data['description'], port_description)

        # check their relations id
        test_cable_id = updated_data['connected_to'][0]['id']
        test_pport_id = updated_data['parent'][0]['id']

        self.assertEqual(cable_id, test_cable_id)
        self.assertEqual(pport_id, test_pport_id)

        # check cable in both payload and metatype attribute
        check_cables = [
            result_data['subupdated'][0]['cable'],
            updated_data['connected_to'][0],
        ]

        for check_cable in check_cables:
            self.assertEqual(check_cable['name'], cable_name)
            self.assertEqual(check_cable['cable_type']['value'], cable_type)
            self.assertEqual(check_cable['description'], cable_description)

        # check parent port in payload and in metatype attribute
        check_parents = [
            result_data['parent_port_updated'][0]['port'],
            updated_data['parent'][0],
        ]

        for check_parent in check_parents:
            self.assertEqual(check_parent['name'], pport_name)
            self.assertEqual(check_parent['port_type']['value'], pport_type)
            self.assertEqual(check_parent['description'], pport_description)


class PortCableTest(Neo4jGraphQLNetworkTest):
    def test_cable_port(self):
        generator = NetworkFakeDataGenerator()

        cable_name = "Test cable"
        cable_type = "Patch"
        cable_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."

        aport_name = "test-01"
        aport_type = "Schuko"
        aport_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        bport_name = "test-02"
        bport_type = "Schuko"
        bport_description = "Nunc varius suscipit lorem, non posuere nisl "\
            "consequat in. Nulla gravida sapien a velit aliquet, aliquam "\
            "tincidunt urna ultrices. Vivamus venenatis ligula a erat "\
            "fringilla faucibus. Suspendisse potenti. Donec rutrum eget "\
            "nunc sed volutpat. Curabitur sit amet lorem elementum sapien "\
            "ornare placerat."

        # set a provider
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # use sunet fields on cable only if they're enabled
        cable_contract = None
        cable_circuitid = None

        sunet_input = ''
        sunet_query = ''

        if sunet_forms_enabled():
            cable_contract = random.choice(
                Dropdown.objects.get(name="tele2_cable_contracts").as_choices()[1:][1]
            )
            cable_circuitid = generator.escape_quotes(generator.fake.ean8())

            sunet_input = '''
                tele2_cable_contract: "{cable_contract}"
                tele2_alternative_circuit_id: "{cable_circuitid}"
            '''.format(
                cable_contract=cable_contract,
                cable_circuitid=cable_circuitid
            )

            sunet_query = '''
                tele2_cable_contract{
                  value
                }
                tele2_alternative_circuit_id
            '''

        # Create query
        query = '''
        mutation{{
          composite_cable(input:{{
            create_input:{{
              name: "{cable_name}"
              cable_type: "{cable_type}"
              description: "{cable_description}"
              relationship_provider: "{provider_id}"
              {sunet_input}
            }}
            create_subinputs:[
              {{
                name: "{aport_name}"
                port_type: "{aport_type}"
                description: "{aport_description}"
              }},
              {{
                name: "{bport_name}"
                port_type: "{bport_type}"
                description: "{bport_description}"
              }}
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              cable{{
                id
                name
                cable_type{{
                  value
                }}
                description
                ports{{
                  id
                  name
                  port_type{{
                    value
                  }}
                  description
                  connected_to{{
                    id
                    name
                  }}
                }}
                provider{{
                  id
                  name
                }}
                {sunet_query}
              }}
            }}
            subcreated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  value
                }}
                description
                connected_to{{
                  id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(cable_name=cable_name, cable_type=cable_type,
                    cable_description=cable_description, aport_name=aport_name,
                    aport_type=aport_type, aport_description=aport_description,
                    bport_name=bport_name, bport_type=bport_type,
                    bport_description=bport_description,
                    provider_id=provider_id, sunet_input=sunet_input,
                    sunet_query=sunet_query)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_cable']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_cable']['subcreated']:
            assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

        # get the ids
        result_data = result.data['composite_cable']
        cable_id = result_data['created']['cable']['id']
        aport_id = result_data['subcreated'][0]['port']['id']
        bport_id = result_data['subcreated'][1]['port']['id']

        # check the integrity of the data
        created_data = result_data['created']['cable']

        # check main cable
        self.assertEqual(created_data['name'], cable_name)
        self.assertEqual(created_data['cable_type']['value'], cable_type)
        self.assertEqual(created_data['description'], cable_description)

        if sunet_forms_enabled():
            self.assertEqual(created_data['tele2_cable_contract']['value'],
                                cable_contract)
            self.assertEqual(created_data['tele2_alternative_circuit_id'],
                                cable_circuitid)

        # check their relations id
        test_aport_id = created_data['ports'][0]['id']
        test_bport_id = created_data['ports'][1]['id']

        self.assertEqual(aport_id, test_aport_id)
        self.assertEqual(bport_id, test_bport_id)

        # check ports in both payload and metatype attribute
        check_aports = [
            created_data['ports'][0],
            result_data['subcreated'][0]['port'],
        ]

        for check_aport in check_aports:
            self.assertEqual(check_aport['name'], aport_name)
            self.assertEqual(check_aport['port_type']['value'], aport_type)
            self.assertEqual(check_aport['description'], aport_description)

        check_bports = [
            created_data['ports'][1],
            result_data['subcreated'][1]['port'],
        ]

        for check_bport in check_bports:
            self.assertEqual(check_bport['name'], bport_name)
            self.assertEqual(check_bport['port_type']['value'], bport_type)
            self.assertEqual(check_bport['description'], bport_description)

        # check provider
        check_provider = result_data['created']['cable']['provider']
        self.assertEqual(check_provider['id'], provider_id)
        self.assertEqual(check_provider['name'], provider.node_name)

        ## Update query
        # (do it two times to check that the relationship id is not overwritten)
        relation_id = None
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        for i in range(2):
            buffer_description = cable_description
            buffer_description2 = aport_description

            cable_name = "New cable"
            cable_type = "Patch"
            cable_description = bport_description

            aport_name = "port-01"
            aport_type = "RJ45"
            aport_description = buffer_description2

            bport_name = "port-02"
            bport_type = "RJ45"
            bport_description = buffer_description

            sunet_input = ''
            sunet_query = ''

            if sunet_forms_enabled():
                cable_contract = random.choice(
                    Dropdown.objects.get(name="tele2_cable_contracts").as_choices()[1:][1]
                )
                cable_circuitid = generator.escape_quotes(generator.fake.ean8())

                sunet_input = '''
                    tele2_cable_contract: "{cable_contract}"
                    tele2_alternative_circuit_id: "{cable_circuitid}"
                '''.format(
                    cable_contract=cable_contract,
                    cable_circuitid=cable_circuitid
                )

                sunet_query = '''
                    tele2_cable_contract{
                      value
                    }
                    tele2_alternative_circuit_id
                '''

            query = '''
            mutation{{
              composite_cable(input:{{
                update_input:{{
                  id: "{cable_id}"
                  name: "{cable_name}"
                  cable_type: "{cable_type}"
                  description: "{cable_description}"
                  relationship_provider: "{provider_id}"
                  {sunet_input}
                }}
                update_subinputs:[
                  {{
                    id: "{aport_id}"
                    name: "{aport_name}"
                    port_type: "{aport_type}"
                    description: "{aport_description}"
                  }},
                  {{
                    id: "{bport_id}"
                    name: "{bport_name}"
                    port_type: "{bport_type}"
                    description: "{bport_description}"
                  }}
                ]
              }}){{
                updated{{
                  errors{{
                    field
                    messages
                  }}
                  cable{{
                    id
                    name
                    cable_type{{
                      value
                    }}
                    description
                    ports{{
                      id
                      name
                      port_type{{
                        value
                      }}
                      description
                      connected_to{{
                        id
                        name
                      }}
                    }}
                    provider{{
                      id
                      name
                      relation_id
                    }}
                    {sunet_query}
                  }}
                }}
                subupdated{{
                  errors{{
                    field
                    messages
                  }}
                  port{{
                    id
                    name
                    port_type{{
                      value
                    }}
                    description
                    connected_to{{
                      id
                      name
                    }}
                  }}
                }}
              }}
            }}
            '''.format(cable_name=cable_name, cable_type=cable_type,
                        cable_description=cable_description, aport_name=aport_name,
                        aport_type=aport_type, aport_description=aport_description,
                        bport_name=bport_name, bport_type=bport_type,
                        bport_description=bport_description, cable_id=cable_id,
                        aport_id=aport_id, bport_id=bport_id,
                        provider_id=provider_id, sunet_input=sunet_input,
                        sunet_query=sunet_query)

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            # check for errors
            created_errors = result.data['composite_cable']['updated']['errors']
            assert not created_errors, pformat(created_errors, indent=1)

            for subcreated in result.data['composite_cable']['subupdated']:
                assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

            # check the integrity of the data
            result_data = result.data['composite_cable']
            updated_data = result_data['updated']['cable']

            # check main cable
            self.assertEqual(updated_data['name'], cable_name)
            self.assertEqual(updated_data['cable_type']['value'], cable_type)
            self.assertEqual(updated_data['description'], cable_description)

            if sunet_forms_enabled():
                self.assertEqual(updated_data['tele2_cable_contract']['value'],
                                    cable_contract)
                self.assertEqual(updated_data['tele2_alternative_circuit_id'],
                                    cable_circuitid)

            # check their relations id
            test_aport_id = updated_data['ports'][0]['id']
            test_bport_id = updated_data['ports'][1]['id']

            self.assertEqual(aport_id, test_aport_id)
            self.assertEqual(bport_id, test_bport_id)

            # check ports in both payload and metatype attribute
            check_aports = [
                updated_data['ports'][0],
                result_data['subupdated'][0]['port'],
            ]

            for check_aport in check_aports:
                self.assertEqual(check_aport['name'], aport_name)
                self.assertEqual(check_aport['port_type']['value'], aport_type)
                self.assertEqual(check_aport['description'], aport_description)

            check_bports = [
                updated_data['ports'][1],
                result_data['subupdated'][1]['port'],
            ]

            for check_bport in check_bports:
                self.assertEqual(check_bport['name'], bport_name)
                self.assertEqual(check_bport['port_type']['value'], bport_type)
                self.assertEqual(check_bport['description'], bport_description)

            # check provider
            check_provider = result_data['updated']['cable']['provider']
            self.assertEqual(check_provider['id'], provider_id)
            self.assertEqual(check_provider['name'], provider.node_name)

            # check that we only have one provider
            _type, cable_handle_id = relay.Node.from_global_id(cable_id)
            cable_nh = NodeHandle.objects.get(handle_id=cable_handle_id)
            cable_node = cable_nh.get_node()
            previous_rels = cable_node.incoming.get('Provides', [])
            self.assertTrue(len(previous_rels) == 1)

            # check relation_id
            if not relation_id: # first run
                relation_id = check_provider['relation_id']
                self.assertIsNotNone(relation_id)
            else:
                self.assertEqual(relation_id, check_provider['relation_id'])

        ## Update query 2 (remove provider)
        query = '''
        mutation{{
          composite_cable(input:{{
            update_input:{{
              id: "{cable_id}"
              name: "{cable_name}"
              cable_type: "{cable_type}"
              description: "{cable_description}"
            }}
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              cable{{
                id
                name
                cable_type{{
                  name
                  value
                }}
                description
                provider{{
                  id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(cable_id=cable_id, cable_name=cable_name, cable_type=cable_type,
                    cable_description=cable_description)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_cable']['updated']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        # check empty provider
        check_provider = result.data['composite_cable']['updated']['cable']['provider']
        self.assertEqual(check_provider, None)


class SwitchTest(Neo4jGraphQLNetworkTest):
    def test_switch(self):
        # create test switchtype and test query
        test_switchtype = SwitchType(
            name="Testlink",
            ports="80,8000"
        )
        test_switchtype.save()

        query = '''
        {
          getSwitchTypes{
            id
            name
            ports
          }
        }
        '''

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        expected_switchtypes = [
            {
                'id': None,
                'name': test_switchtype.name,
                'ports': test_switchtype.ports,
            }
        ]

        switch_types = result.data['getSwitchTypes']
        self.assertTrue(len(switch_types) == 1)

        switchtype_id = switch_types[0]['id']
        expected_switchtypes[0]['id'] = switchtype_id
        self.assertEquals(switch_types, expected_switchtypes)

        # get a provider
        generator = NetworkFakeDataGenerator()
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # get a location
        location = generator.create_rack()
        location_id = relay.Node.to_global_id(str(location.node_type),
                                                str(location.handle_id))

        # get two groups
        community_generator = CommunityFakeDataGenerator()
        group1 = community_generator.create_group()
        group2 = community_generator.create_group()

        group1_id = relay.Node.to_global_id(str(group1.node_type),
                                            str(group1.handle_id))
        group2_id = relay.Node.to_global_id(str(group2.node_type),
                                            str(group2.handle_id))

        # create switch
        switch_name = "Test switch"
        switch_description = "Created from graphql"
        ip_addresses = ["127.0.0.1", "168.192.0.1"]
        operational_state = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:][1]
        )

        rack_units = 2
        rack_position = 3
        rack_back = bool(random.getrandbits(1))

        managed_by = random.choice(
            Dropdown.objects.get(name="host_management_sw").as_choices()[1:][1]
        )
        backup = "Manual script"
        os = "GNU/Linux"
        os_version = "5.8"
        contract_number = "001"
        max_number_of_ports = 20
        services_locked = bool(random.getrandbits(1))

        # create new port
        port_1_name = str(random.randint(0, 50000))
        port_1_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:][1]
        )
        port_1_description = generator.escape_quotes(generator.fake.paragraph())

        # add existent port
        port = generator.create_port()
        port_2_id = relay.Node.to_global_id(str(port.node_type),
                                            str(port.handle_id))
        port_2_name = str(random.randint(0, 50000))
        port_2_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:][1]
        )
        port_2_description = generator.escape_quotes(generator.fake.paragraph())

        query = '''
        mutation{{
          composite_switch(
            input:{{
              create_input: {{
                name: "{switch_name}"
                description: "{switch_description}"
                switch_type: "{switchtype_id}"
                ip_addresses: "{ip_address}"
                rack_units: {rack_units}
                rack_position: {rack_position}
                rack_back: {rack_back}
                operational_state: "{operational_state}"
                relationship_provider: "{provider_id}"
                responsible_group: "{group1_id}"
                support_group: "{group2_id}"
                managed_by: "{managed_by}"
                backup: "{backup}"
                os: "{os}"
                os_version: "{os_version}"
                contract_number: "{contract_number}"
                max_number_of_ports: {max_number_of_ports}
                services_locked: {services_locked}
                relationship_location: "{location_id}"
              }}
              create_subinputs:[
                {{
                  name: "{port_1_name}"
                  port_type: "{port_1_type}"
                  description: "{port_1_description}"
                }}
              ]
              update_subinputs:[
                {{
                  id: "{port_2_id}"
                  name: "{port_2_name}"
                  port_type: "{port_2_type}"
                  description: "{port_2_description}"
                }}
              ]
            }}
          ){{
            created{{
              errors{{
                field
                messages
              }}
              switch{{
                id
                name
                description
                ip_addresses
                rack_units
                rack_position
                rack_back
                services_locked
                services_checked
                provider{{
                  id
                  name
                }}
                responsible_group{{
                  id
                  name
                }}
                support_group{{
                  id
                  name
                }}
                managed_by{{
                  value
                }}
                backup
                os
                os_version
                contract_number
                max_number_of_ports
                ports{{
                  id
                  name
                }}
                location{{
                  id
                  name
                }}
              }}
            }}
            subcreated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  name
                  value
                }}
                description
              }}
            }}
            subupdated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  name
                  value
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(switch_name=switch_name, switch_description=switch_description,
                    switchtype_id=switchtype_id, ip_address="\\n".join(ip_addresses),
                    rack_units=rack_units, rack_position=rack_position,
                    operational_state=operational_state, provider_id=provider_id,
                    group1_id=group1_id, group2_id=group2_id,
                    managed_by=managed_by, backup=backup, os=os,
                    os_version=os_version, contract_number=contract_number,
                    max_number_of_ports=max_number_of_ports,
                    port_1_name=port_1_name, port_1_type=port_1_type,
                    port_1_description=port_1_description,
                    port_2_name=port_2_name, port_2_type=port_2_type,
                    port_2_description=port_2_description, port_2_id=port_2_id,
                    rack_back=str(rack_back).lower(),
                    services_locked=str(services_locked).lower(),
                    location_id=location_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_switch']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        # store the created switch id
        created_switch = result.data['composite_switch']['created']['switch']
        switch_id = created_switch['id']

        # check data
        self.assertEqual(created_switch['name'], switch_name)
        self.assertEqual(created_switch['description'], switch_description)
        self.assertEqual(created_switch['rack_units'], rack_units)
        self.assertEqual(created_switch['rack_position'], rack_position)
        self.assertEqual(created_switch['rack_back'], rack_back)
        self.assertEqual(created_switch['ip_addresses'], ip_addresses)
        self.assertEqual(created_switch['managed_by']['value'], managed_by)
        self.assertEqual(created_switch['backup'], backup)
        self.assertEqual(created_switch['os'], os)
        self.assertEqual(created_switch['os_version'], os_version)
        self.assertEqual(created_switch['contract_number'], contract_number)
        self.assertEqual(created_switch['max_number_of_ports'], max_number_of_ports)
        self.assertEqual(created_switch['services_locked'], services_locked)

        # check provider
        check_provider = created_switch['provider']
        self.assertEqual(check_provider['id'], provider_id)

        # check location
        check_location = created_switch['location']
        self.assertEqual(check_location['id'], location_id)

        # check responsible group
        check_responsible = created_switch['responsible_group']
        self.assertEqual(check_responsible['id'], group1_id)

        # check support group
        check_support = created_switch['support_group']
        self.assertEqual(check_support['id'], group2_id)

        # check ports data

        # check port_1 data
        created_checkport = result.data['composite_switch']['subcreated'][0]
        created_errors = created_checkport['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        created_checkport = created_checkport['port']
        port_1_id = created_checkport['id']

        self.assertEqual(created_checkport['name'], port_1_name)
        self.assertEqual(created_checkport['port_type']['value'], port_1_type)
        self.assertEqual(created_checkport['description'], port_1_description)

        # check port_2
        update_checkport = result.data['composite_switch']['subupdated'][0]
        updated_errors = update_checkport['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        update_checkport = update_checkport['port']
        self.assertEqual(update_checkport['name'], port_2_name)
        self.assertEqual(update_checkport['port_type']['value'], port_2_type)
        self.assertEqual(update_checkport['description'], port_2_description)

        # check ports in router
        self.assertEqual(created_switch['ports'][1]['id'], port_1_id)
        self.assertEqual(created_switch['ports'][0]['id'], port_2_id)

        ## simple update
        # get another provider
        generator = NetworkFakeDataGenerator()
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        switch_name = "New Switch"
        switch_description = "Updated from graphql"
        ip_addresses = ["127.0.0.1", "168.192.0.1", "0.0.0.0"]
        operational_state = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:][1]
        )

        rack_units = 3
        rack_position = 2
        rack_back = bool(random.getrandbits(1))

        managed_by = random.choice(
            Dropdown.objects.get(name="host_management_sw").as_choices()[1:][1]
        )
        backup = "Jenkins script"
        os = "Linux"
        os_version = "5.7"
        contract_number = "002"
        max_number_of_ports = 15
        services_locked = bool(random.getrandbits(1))

        query = '''
        mutation{{
          composite_switch(
            input:{{
              update_input: {{
                id: "{switch_id}"
                name: "{switch_name}"
                description: "{switch_description}"
                ip_addresses: "{ip_address}"
                rack_units: {rack_units}
                rack_position: {rack_position}
                rack_back: {rack_back}
                operational_state: "{operational_state}"
                relationship_provider: "{provider_id}"
                responsible_group: "{group2_id}"
                support_group: "{group1_id}"
                managed_by: "{managed_by}"
                backup: "{backup}"
                os: "{os}"
                os_version: "{os_version}"
                contract_number: "{contract_number}"
                max_number_of_ports: {max_number_of_ports}
                services_locked: {services_locked}
              }}
            }}
          ){{
            updated{{
              errors{{
                field
                messages
              }}
              switch{{
                id
                name
                description
                ip_addresses
                rack_units
                rack_position
                rack_back
                services_locked
                services_checked
                provider{{
                  id
                  name
                }}
                responsible_group{{
                  id
                  name
                }}
                support_group{{
                  id
                  name
                }}
                managed_by{{
                  value
                }}
                location{{
                  id
                  name
                }}
                backup
                os
                os_version
                contract_number
                max_number_of_ports
              }}
            }}
          }}
        }}
        '''.format(switch_name=switch_name, switch_id=switch_id,
                    switch_description=switch_description,
                    ip_address="\\n".join(ip_addresses),
                    rack_units=rack_units, rack_position=rack_position,
                    operational_state=operational_state, provider_id=provider_id,
                    group1_id=group1_id, group2_id=group2_id,
                    managed_by=managed_by, backup=backup, os=os,
                    os_version=os_version, contract_number=contract_number,
                    max_number_of_ports=max_number_of_ports,
                    rack_back=str(rack_back).lower(),
                    services_locked=str(services_locked).lower())

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_switch']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        # check data
        updated_switch = result.data['composite_switch']['updated']['switch']

        self.assertEqual(updated_switch['name'], switch_name)
        self.assertEqual(updated_switch['description'], switch_description)
        self.assertEqual(updated_switch['rack_units'], rack_units)
        self.assertEqual(updated_switch['rack_position'], rack_position)
        self.assertEqual(updated_switch['rack_back'], rack_back)
        self.assertEqual(updated_switch['ip_addresses'], ip_addresses)
        self.assertEqual(updated_switch['managed_by']['value'], managed_by)
        self.assertEqual(updated_switch['backup'], backup)
        self.assertEqual(updated_switch['os'], os)
        self.assertEqual(updated_switch['os_version'], os_version)
        self.assertEqual(updated_switch['contract_number'], contract_number)
        self.assertEqual(updated_switch['max_number_of_ports'], max_number_of_ports)
        self.assertEqual(updated_switch['services_locked'], services_locked)

        # check provider
        check_provider = updated_switch['provider']
        self.assertEqual(check_provider['id'], provider_id)

        # check responsible group
        check_responsible = updated_switch['responsible_group']
        self.assertEqual(check_responsible['id'], group2_id)

        # check support group
        check_support = updated_switch['support_group']
        self.assertEqual(check_support['id'], group1_id)

        # check location
        check_location = updated_switch['location']
        self.assertEqual(check_location, None)

        # set empty group relations
        query = '''
        mutation{{
          composite_switch(
            input:{{
              update_input: {{
                id: "{switch_id}"
                name: "{switch_name}"
                description: "{switch_description}"
                ip_addresses: "{ip_address}"
                rack_units: {rack_units}
                rack_position: {rack_position}
                operational_state: "{operational_state}"
                managed_by: "{managed_by}"
                backup: "{backup}"
                os: "{os}"
                os_version: "{os_version}"
                contract_number: "{contract_number}"
                max_number_of_ports: {max_number_of_ports}
              }}
            }}
          ){{
            updated{{
              errors{{
                field
                messages
              }}
              switch{{
                id
                name
                provider{{
                  id
                  name
                }}
                responsible_group{{
                  id
                  name
                }}
                support_group{{
                  id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(switch_name=switch_name, switch_id=switch_id,
                    switch_description=switch_description,
                    ip_address="\\n".join(ip_addresses),
                    rack_units=rack_units, rack_position=rack_position,
                    operational_state=operational_state,
                    managed_by=managed_by, backup=backup, os=os,
                    os_version=os_version, contract_number=contract_number,
                    max_number_of_ports=max_number_of_ports)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_switch']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        updated_switch = result.data['composite_switch']['updated']['switch']

        # check that these values had been set to none/null
        self.assertEqual(updated_switch['provider'], None)
        self.assertEqual(updated_switch['responsible_group'], None)
        self.assertEqual(updated_switch['support_group'], None)


class RouterTest(Neo4jGraphQLNetworkTest):
    def test_router(self):
        # as we can't create routers from the graphql API
        # we create a new dummy router
        generator = NetworkFakeDataGenerator()
        router = generator.create_router()
        router_id = relay.Node.to_global_id(str(router.node_type),
                                            str(router.handle_id))

        # get new data to feed the update mutation
        rack_units = random.randint(1,10)
        rack_position = random.randint(1,10)
        rack_back = bool(random.getrandbits(1))

        operational_state = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:][1]
        )
        description = generator.escape_quotes(generator.fake.paragraph())

        # ports vars
        port_1_name = str(random.randint(0, 50000))
        port_1_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:][1]
        )
        port_1_description = generator.escape_quotes(generator.fake.paragraph())

        port_2 = generator.create_port()
        port_2_id = relay.Node.to_global_id(str(port_2.node_type),
                                            str(port_2.handle_id))
        port_2_name = str(random.randint(0, 50000))
        port_2_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:][1]
        )
        port_2_description = generator.escape_quotes(generator.fake.paragraph())

        # location
        location = generator.create_rack()
        location_id = relay.Node.to_global_id(str(location.node_type),
                                                str(location.handle_id))

        query = '''
        mutation{{
          composite_router(input:{{
            update_input:{{
              id: "{router_id}"
              description: "{description}"
              operational_state: "{operational_state}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
              relationship_location: "{location_id}"
            }}
            create_subinputs:[
              {{
                name: "{port_1_name}"
                port_type: "{port_1_type}"
                description: "{port_1_description}"
              }}
            ]
            update_subinputs:[
              {{
                id: "{port_2_id}"
                name: "{port_2_name}"
                port_type: "{port_2_type}"
                description: "{port_2_description}"
              }}
            ]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              router{{
                id
                name
                description
                operational_state{{
                  name
                  value
                }}
                model
                version
                rack_units
                rack_position
                rack_back
                location{{
                  id
                  name
                }}
                ports{{
                  id
                  name
                }}
              }}
            }}
            subcreated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  name
                  value
                }}
                description
              }}
            }}
            subupdated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  name
                  value
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(router_id=router_id, description=description,
                    operational_state=operational_state, rack_units=rack_units,
                    rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port_1_name=port_1_name, port_1_type=port_1_type,
                    port_1_description=port_1_description,
                    port_2_id=port_2_id, port_2_name=port_2_name,
                    port_2_type=port_2_type,
                    port_2_description=port_2_description,
                    location_id=location_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_router']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        # check router data
        updated_router = result.data['composite_router']['updated']['router']

        self.assertEqual(updated_router['description'], description)
        self.assertEqual(updated_router['operational_state']['value'],\
            operational_state)
        self.assertEqual(updated_router ['rack_units'], rack_units)
        self.assertEqual(updated_router['rack_position'], rack_position)
        self.assertEqual(updated_router['rack_back'], rack_back)

        # check ports data

        # check port_1 data
        created_checkport = result.data['composite_router']['subcreated'][0]
        created_errors = created_checkport['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        created_checkport = created_checkport['port']
        port_1_id = created_checkport['id']

        self.assertEqual(created_checkport['name'], port_1_name)
        self.assertEqual(created_checkport['port_type']['value'], port_1_type)
        self.assertEqual(created_checkport['description'], port_1_description)

        # check port_2
        update_checkport = result.data['composite_router']['subupdated'][0]
        updated_errors = update_checkport['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        update_checkport = update_checkport['port']
        self.assertEqual(update_checkport['name'], port_2_name)
        self.assertEqual(update_checkport['port_type']['value'], port_2_type)
        self.assertEqual(update_checkport['description'], port_2_description)

        # check ports in router
        self.assertEqualIds(updated_router['ports'][1]['id'], port_1_id)
        self.assertEqualIds(updated_router['ports'][0]['id'], port_2_id)

        # check location
        self.assertEqual(updated_router['location']['id'], location_id)


class FirewallTest(Neo4jGraphQLNetworkTest):
    def test_firewall(self):
        net_generator = NetworkFakeDataGenerator()
        firewall = net_generator.create_firewall()

        firewall_id = relay.Node.to_global_id(str(firewall.node_type),
                                            str(firewall.handle_id))
        firewall_name = "Test firewall"
        firewall_description = "Created from graphql"
        operational_state = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:][1]
        )
        managed_by = random.choice(
            Dropdown.objects.get(name="host_management_sw").as_choices()[1:][1]
        )

        # get two groups
        com_generator = CommunityFakeDataGenerator()
        group1 = com_generator.create_group()
        group2 = com_generator.create_group()

        group1_id = relay.Node.to_global_id(str(group1.node_type),
                                            str(group1.handle_id))
        group2_id = relay.Node.to_global_id(str(group2.node_type),
                                            str(group2.handle_id))

        backup = "Manual script"
        security_class = random.choice(
            Dropdown.objects.get(name="security_classes").as_choices()[1:][1]
        )
        security_comment = "It's updated manually"
        os = "GNU/Linux"
        os_version = "5.8"
        model = com_generator.escape_quotes(com_generator.fake.license_plate())
        vendor = com_generator.company_name()
        service_tag = com_generator.escape_quotes(com_generator.fake.license_plate())
        end_support = "2020-06-23"
        contract_number = "001"
        max_number_of_ports = 20
        rack_position = 3
        rack_units = 2
        rack_back = bool(random.getrandbits(1))
        services_locked = bool(random.getrandbits(1))

        # owner and location
        owner = net_generator.create_end_user()
        owner_id = relay.Node.to_global_id(str(owner.node_type).replace(' ', ''),
                                            str(owner.handle_id))

        location = net_generator.create_rack()
        location_id = relay.Node.to_global_id(str(location.node_type),
                                                str(location.handle_id))

        # create new port
        port_1_name = str(random.randint(0, 50000))
        port_1_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:][1]
        )
        port_1_description = net_generator.escape_quotes(net_generator.fake.paragraph())

        # add existent port
        port = net_generator.create_port()
        port_2_id = relay.Node.to_global_id(str(port.node_type),
                                            str(port.handle_id))
        port_2_name = str(random.randint(0, 50000))
        port_2_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:][1]
        )
        port_2_description = net_generator.escape_quotes(net_generator.fake.paragraph())

        query = '''
        mutation{{
          composite_firewall(input:{{
            update_input:{{
              id: "{firewall_id}"
              name: "{firewall_name}"
              description: "{firewall_description}"
              operational_state: "{operational_state}"
              managed_by: "{managed_by}"
              responsible_group: "{group1_id}"
              support_group: "{group2_id}"
              backup: "{backup}"
              security_class: "{security_class}"
              security_comment: "{security_comment}"
              os: "{os}"
              os_version: "{os_version}"
              model: "{model}"
              vendor: "{vendor}"
              service_tag: "{service_tag}"
              end_support: "{end_support}"
              contract_number: "{contract_number}"
              max_number_of_ports: {max_number_of_ports}
              rack_units: {rack_units}
              rack_position: {rack_position}
              services_locked: {services_locked}
              rack_back: {rack_back}
              relationship_owner: "{owner_id}"
              relationship_location: "{location_id}"
            }}
            create_has_port:[
              {{
                name: "{port_1_name}"
                port_type: "{port_1_type}"
                description: "{port_1_description}"
              }}
            ]
            update_has_port:[
              {{
                id: "{port_2_id}"
                name: "{port_2_name}"
                port_type: "{port_2_type}"
                description: "{port_2_description}"
              }}
            ]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              firewall{{
                id
                name
                description
                operational_state{{
                  value
                }}
                managed_by{{
                  id
                  value
                }}
                responsible_group{{
                  id
                  name
                }}
                support_group{{
                  id
                  name
                }}
                backup
                security_class{{
                  name
                  value
                }}
                security_comment
                os
                os_version
                model
                vendor
                service_tag
                end_support
                max_number_of_ports
                rack_units
                rack_position
                rack_back
                services_locked
                services_checked
                contract_number
                ports{{
                  id
                  name
                }}
                location{{
                  id
                  name
                }}
                owner{{
                  id
                  name
                }}
              }}
            }}
            has_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  name
                  value
                }}
                description
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  name
                  value
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_description=firewall_description,
            operational_state=operational_state, managed_by=managed_by,
            group1_id=group1_id, group2_id=group2_id, backup=backup,
            security_class=security_class, security_comment=security_comment,
            os=os, os_version=os_version, model=model, vendor=vendor,
            service_tag=service_tag, end_support=end_support,
            contract_number=contract_number, owner_id=owner_id,
            location_id=location_id,
            max_number_of_ports=max_number_of_ports, rack_units=rack_units,
            rack_position=rack_position, rack_back=str(rack_back).lower(),
            services_locked=str(services_locked).lower(),
            port_1_name=port_1_name, port_1_type=port_1_type,
            port_1_description=port_1_description,
            port_2_name=port_2_name, port_2_type=port_2_type,
            port_2_description=port_2_description, port_2_id=port_2_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = result.data['composite_firewall']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        updated_firewall = result.data['composite_firewall']['updated']['firewall']
        self.assertEqual(updated_firewall['name'], firewall_name)
        self.assertEqual(updated_firewall['description'], firewall_description)
        self.assertEqual(updated_firewall['operational_state']['value'], operational_state)
        self.assertEqual(updated_firewall['managed_by']['value'], managed_by)
        self.assertEqual(updated_firewall['security_class']['value'], security_class)
        self.assertEqual(updated_firewall['security_comment'], security_comment)
        self.assertEqual(updated_firewall['os'], os)
        self.assertEqual(updated_firewall['os_version'], os_version)
        self.assertEqual(updated_firewall['model'], model)
        self.assertEqual(updated_firewall['vendor'], vendor)
        self.assertEqual(updated_firewall['end_support'], end_support)
        self.assertEqual(updated_firewall['max_number_of_ports'], max_number_of_ports)
        self.assertEqual(updated_firewall['rack_units'], rack_units)
        self.assertEqual(updated_firewall['rack_position'], rack_position)
        self.assertEqual(updated_firewall['rack_back'], rack_back)
        self.assertEqual(updated_firewall['contract_number'], contract_number)
        self.assertEqual(updated_firewall['services_locked'], services_locked)

        # check responsible group
        check_responsible = updated_firewall['responsible_group']
        self.assertEqual(check_responsible['id'], group1_id)

        # check support group
        check_support = updated_firewall['support_group']
        self.assertEqual(check_support['id'], group2_id)

        # check owner and location
        check_owner = updated_firewall['owner']
        self.assertEqualIds(check_owner['id'], owner_id)

        check_location = updated_firewall['location']
        self.assertEqualIds(check_location['id'], location_id)

        # check ports data

        # check port_1 data
        created_checkport = result.data['composite_firewall']['has_port_created'][0]
        created_errors = created_checkport['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        created_checkport = created_checkport['port']
        port_1_id = created_checkport['id']

        self.assertEqual(created_checkport['name'], port_1_name)
        self.assertEqual(created_checkport['port_type']['value'], port_1_type)
        self.assertEqual(created_checkport['description'], port_1_description)

        # check port_2
        update_checkport = result.data['composite_firewall']['has_port_updated'][0]
        updated_errors = update_checkport['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        update_checkport = update_checkport['port']
        self.assertEqual(update_checkport['name'], port_2_name)
        self.assertEqual(update_checkport['port_type']['value'], port_2_type)
        self.assertEqual(update_checkport['description'], port_2_description)

        # check ports in router
        self.assertEqual(updated_firewall['ports'][1]['id'], port_1_id)
        self.assertEqual(updated_firewall['ports'][0]['id'], port_2_id)

        # delete owner submutation test
        query = '''
        mutation{{
          composite_firewall(input:{{
            update_input:{{
              id: "{firewall_id}"
              name: "{firewall_name}"
              operational_state: "{operational_state}"
            }}
            delete_owner:{{
              id: "{owner_id}"
            }}
          }}){{
            deleted_owner{{
              errors{{
                field
                messages
              }}
              success
            }}
          }}
        }}
        '''.format(firewall_id=firewall_id, firewall_name=firewall_name,
                    operational_state=operational_state, owner_id=owner_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        deleted_errors = \
            result.data['composite_firewall']['deleted_owner']['errors']
        assert not deleted_errors, pformat(deleted_errors, indent=1)

        # check is successful
        success = result.data['composite_firewall']['deleted_owner']['success']
        self.assertTrue(success)


class ExternalEquipmentTest(Neo4jGraphQLNetworkTest):
    def test_external_equipment(self):
        # external equipment data
        exteq_name = "External Equipment test"
        exteq_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = 2
        rack_position = 3
        rack_back = bool(random.getrandbits(1))

        # port data
        port1_name = "test-01"
        port1_type = "Schuko"
        port1_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        # generate second port
        net_generator = NetworkFakeDataGenerator()
        port2 = net_generator.create_port()
        port2_name = port2.node_name
        port2_description = port2.get_node().data.get('description')
        port2_type = port2.get_node().data.get('port_type')
        port2_id = relay.Node.to_global_id(str(port2.node_type),
                                            str(port2.handle_id))

        # generate owner
        owner = net_generator.create_end_user()
        owner_id = relay.Node.to_global_id(str(owner.node_type).replace(' ', ''),
                                            str(owner.handle_id))

        # get a location
        location = net_generator.create_rack()
        location_id = relay.Node.to_global_id(str(location.node_type),
                                                str(location.handle_id))

        query = '''
        mutation{{
          composite_externalEquipment(input:{{
            create_input:{{
              name: "{exteq_name}"
              description: "{exteq_description}"
              relationship_owner: "{owner_id}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
              relationship_location: "{location_id}"
            }}
            create_has_port:[
              {{
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
          	update_has_port:[
              {{
                id: "{port2_id}"
                name: "{port2_name}"
                description: "{port2_description}"
                port_type: "{port2_type}"
              }},
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              externalEquipment{{
                id
                name
                description
                rack_units
                rack_position
                rack_back
                owner{{
                  id
                  name
                }}
                has{{
                  id
                  name
                }}
                location{{
                  id
                  name
                }}
              }}
            }}
            has_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
          }}
        }}
        '''.format(exteq_name=exteq_name, exteq_description=exteq_description,
                    owner_id=owner_id, rack_units=rack_units,
                    rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port1_name=port1_name,
                    port1_type=port1_type, port1_description=port1_description,
                    port2_id=port2_id, port2_name=port2_name,
                    port2_type=port2_type, port2_description=port2_description,
                    location_id=location_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = \
            result.data['composite_externalEquipment']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        subcreated_errors = \
            result.data['composite_externalEquipment']['has_port_created'][0]['errors']
        assert not subcreated_errors, pformat(subcreated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_externalEquipment']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        # check data
        created_extequip = result.data['composite_externalEquipment']['created']['externalEquipment']
        exteq_id = created_extequip['id']

        self.assertEqual(created_extequip['name'], exteq_name)
        self.assertEqual(created_extequip['description'], exteq_description)
        self.assertEqual(created_extequip['rack_units'], rack_units)
        self.assertEqual(created_extequip['rack_position'], rack_position)
        self.assertEqual(created_extequip['rack_back'], rack_back)

        # check subentities
        port1_id = result.data \
            ['composite_externalEquipment']['has_port_created'][0]['port']['id']
        check_port1 = result.data \
            ['composite_externalEquipment']['has_port_created'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_port2 = result.data \
            ['composite_externalEquipment']['has_port_updated'][0]['port']

        self.assertEqual(check_port2['id'], port2_id)
        self.assertEqual(check_port2['name'], port2_name)
        self.assertEqual(check_port2['description'], port2_description)
        self.assertEqual(check_port2['port_type']['value'], port2_type)

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in created_extequip['has']]

        self.assertTrue(port1_id in has_ids)
        self.assertTrue(port2_id in has_ids)

        # check location
        check_location = created_extequip['location']
        self.assertEqual(check_location['id'], location_id)

        # update query
        exteq_name = "External Equipment check"
        exteq_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = 3
        rack_position = 2

        port1_name = "check-01"
        port1_type = port2_type
        port1_description = port2_description

        query = '''
        mutation{{
          composite_externalEquipment(input:{{
            update_input:{{
              id: "{exteq_id}"
              name: "{exteq_name}"
              description: "{exteq_description}"
              rack_units: {rack_units}
              rack_position: {rack_position}
            }}
          	update_has_port:[
              {{
                id: "{port1_id}"
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
            deleted_has_port:[
              {{
                id: "{port2_id}"
              }}
          	]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              externalEquipment{{
                id
                name
                description
                rack_units
                rack_position
                owner{{
                  id
                  name
                }}
                has{{
                  id
                  name
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_deleted{{
              errors{{
                field
                messages
              }}
              success
            }}
          }}
        }}
        '''.format(exteq_id=exteq_id,exteq_name=exteq_name,
                    exteq_description=exteq_description, rack_units=rack_units,
                    rack_position=rack_position, port1_id=port1_id,
                    port1_name=port1_name, port1_type=port1_type,
                    port1_description=port1_description, port2_id=port2_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = \
            result.data['composite_externalEquipment']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_externalEquipment']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        subdeleted_errors = \
            result.data['composite_externalEquipment']['has_port_deleted'][0]['errors']
        assert not subdeleted_errors, pformat(subdeleted_errors, indent=1)

        # check data
        updated_extequip = result.data['composite_externalEquipment']['updated']['externalEquipment']
        self.assertEqual(updated_extequip['name'], exteq_name)
        self.assertEqual(updated_extequip['description'], exteq_description)
        self.assertEqual(updated_extequip['rack_units'], rack_units)
        self.assertEqual(updated_extequip['rack_position'], rack_position)

        # check subentities
        check_port1 = result.data \
            ['composite_externalEquipment']['has_port_updated'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_deleted_port2 = result.data \
            ['composite_externalEquipment']['has_port_deleted'][0]['success']

        self.assertTrue(check_deleted_port2)

        # check owner is not present
        self.assertIsNone(updated_extequip['owner'])

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in updated_extequip['has']]

        self.assertTrue(port1_id in has_ids)
        self.assertFalse(port2_id in has_ids)


class HostTest(Neo4jGraphQLNetworkTest):
    def test_host(self):
        # create two different hosts: a logical host and a physical host
        # we'll set no owner nor location in order to test a logical host
        # and we'll set these entities to create a physical host
        owner_queries = [
            {
                'input_owner': '',
                'query_owner': '',
            },
            {
                'input_owner': 'relationship_owner: "{owner_id}"',
                'query_owner': '''
                    host_owner {
                      id
                      name
                    }
                ''',
            },
        ]

        location_queries = [
            {
                'input_location': '',
                'query_location': '',
            },
            {
                'input_location': 'relationship_location: "{location_id}"',
                'query_location': '''
                    location {
                      id
                      name
                    }
                ''',
            },
        ]

        host_ids = {
            'logical': None,
            'physical': None,
        }

        for i in range(2):
            owner_query = owner_queries[i]
            location_query = location_queries[i]

            # get two groups
            community_generator = CommunityFakeDataGenerator()
            net_generator = NetworkFakeDataGenerator()

            group1 = community_generator.create_group()
            group2 = community_generator.create_group()

            group1_id = relay.Node.to_global_id(str(group1.node_type),
                                                str(group1.handle_id))
            group2_id = relay.Node.to_global_id(str(group2.node_type),
                                                str(group2.handle_id))

            # create host
            host_name = community_generator.fake.hostname()
            host_description = "Created from graphql"
            ip_addresses = ["127.0.0.1", "168.192.0.1"]
            operational_state = random.choice(
                Dropdown.objects.get(name="operational_states")\
                    .as_choices()[1:][1]
            )

            rack_units = 2
            rack_position = 3
            rack_back = bool(random.getrandbits(1))

            managed_by = random.choice(
                Dropdown.objects.get(name="host_management_sw")\
                    .as_choices()[1:][1]
            )
            backup = "Manual script"
            os = "GNU/Linux"
            os_version = "5.8"
            contract_number = "001"
            services_locked = bool(random.getrandbits(1))

            # owner
            input_owner = owner_query['input_owner']
            query_owner = owner_query['query_owner']

            owner_id = None

            if input_owner:
                owner = net_generator.create_customer()
                owner_id = relay.Node.to_global_id(
                    str(owner.node_type).replace(' ', ''),
                    str(owner.handle_id)
                )
                input_owner = input_owner.format(owner_id=owner_id)

            # location (rack)
            input_location = location_query['input_location']
            query_location = location_query['query_location']

            location_id = None

            if input_location:
                location = net_generator.create_rack()
                location_id = relay.Node.to_global_id(
                    str(location.node_type).replace(' ', ''),
                    str(location.handle_id)
                )
                input_location = input_location.format(
                                        location_id=location_id)

            query = '''
            mutation{{
              composite_host(
                input:{{
                  create_input: {{
                    name: "{host_name}"
                    description: "{host_description}"
                    ip_addresses: "{ip_address}"
                    rack_units: {rack_units}
                    rack_position: {rack_position}
                    rack_back: {rack_back}
                    operational_state: "{operational_state}"
                    responsible_group: "{group1_id}"
                    support_group: "{group2_id}"
                    managed_by: "{managed_by}"
                    backup: "{backup}"
                    os: "{os}"
                    os_version: "{os_version}"
                    contract_number: "{contract_number}"
                    services_locked: {services_locked}
                    {input_owner}
                    {input_location}
                  }}
                }}
              ){{
                created{{
                  errors{{
                    field
                    messages
                  }}
                  host{{
                    id
                    name
                    operational_state{{
                      value
                    }}
                    description
                    host_type
                    ip_addresses
                    responsible_group{{
                      id
                      name
                    }}
                    support_group{{
                      id
                      name
                    }}
                    managed_by{{
                      value
                    }}
                    backup
                    os
                    os_version
                    contract_number
                    rack_units
                    rack_position
                    rack_back
                    services_locked
                    services_checked
                    {query_owner}
                    {query_location}
                  }}
                }}
              }}
            }}
            '''.format(host_name=host_name, host_description=host_description,
                        ip_address="\\n".join(ip_addresses),
                        rack_units=rack_units, rack_position=rack_position,
                        operational_state=operational_state,
                        group1_id=group1_id, group2_id=group2_id,
                        managed_by=managed_by, backup=backup, os=os,
                        os_version=os_version, contract_number=contract_number,
                        rack_back=str(rack_back).lower(),
                        services_locked=str(services_locked).lower(),
                        input_owner=input_owner, query_owner=query_owner,
                        input_location=input_location, query_location=query_location)

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            # check for errors
            created_errors = result.data['composite_host']['created']['errors']
            assert not created_errors, pformat(created_errors, indent=1)

            # store the created host id
            created_host = result.data['composite_host']['created']['host']
            host_id = created_host['id']

            # check data
            self.assertEqual(created_host['name'], host_name)
            self.assertEqual(created_host['description'], host_description)
            self.assertEqual(created_host['operational_state']['value'], operational_state)
            self.assertEqual(created_host['rack_units'], rack_units)
            self.assertEqual(created_host['rack_position'], rack_position)
            self.assertEqual(created_host['rack_back'], rack_back)
            self.assertEqual(created_host['ip_addresses'], ip_addresses)
            self.assertEqual(created_host['managed_by']['value'], managed_by)
            self.assertEqual(created_host['backup'], backup)
            self.assertEqual(created_host['os'], os)
            self.assertEqual(created_host['os_version'], os_version)
            self.assertEqual(created_host['contract_number'], contract_number)
            self.assertEqual(created_host['services_locked'], services_locked)

            # check responsible group
            check_responsible = created_host['responsible_group']
            self.assertEqual(check_responsible['id'], group1_id)

            # check support group
            check_support = created_host['support_group']
            self.assertEqual(check_support['id'], group2_id)

            # check we've created a logical node
            _type, host_handle_id = relay.Node.from_global_id(host_id)
            host_nh = NodeHandle.objects.get(handle_id=host_handle_id)
            host_node = host_nh.get_node()

            if not input_owner:
                self.assertEqual(created_host['host_type'], "Logical")
                self.assertEqual(host_node.meta_type, "Logical")
                host_ids['logical'] = host_id
            else:
                self.assertEqual(created_host['host_type'], "Physical")
                self.assertEqual(host_node.meta_type, "Physical")
                host_ids['physical'] = host_id

                # check owner and location
                self.assertEqual(created_host['host_owner']['id'], owner_id)
                self.assertEqual(created_host['location']['id'], location_id)

        edit_query = '''
        mutation{{
          composite_host(input:{{
            update_input:{{
              id: "{host_id}"
              name: "{host_name}"
              description: "{host_description}"
              ip_addresses: "{ip_address}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
              operational_state: "{operational_state}"
              responsible_group: "{group1_id}"
              support_group: "{group2_id}"
              managed_by: "{managed_by}"
              backup: "{backup}"
              os: "{os}"
              os_version: "{os_version}"
              contract_number: "{contract_number}"
              services_locked: {services_locked}
              {extra_input}
            }}
            {subinputs}
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              host{{
                id
                name
                description
                operational_state{{
                  value
                }}
                host_type
                ip_addresses
                responsible_group{{
                  id
                  name
                }}
                support_group{{
                  id
                  name
                }}
                managed_by{{
                  value
                }}
                backup
                os
                os_version
                contract_number
                rack_units
                rack_position
                rack_back
                services_locked
                services_checked
                {extra_query}
              }}
            }}
            {subquery}
          }}
        }}
        '''

        # create a host user and a different owner
        huser = net_generator.create_host_user()
        huser_id = relay.Node.to_global_id(
            str(huser.node_type).replace(' ', ''),
            str(huser.handle_id)
        )

        owner = net_generator.create_customer()
        owner_id = relay.Node.to_global_id(
            str(owner.node_type).replace(' ', ''),
            str(owner.handle_id)
        )

        host_user_query = {
            'logical':{
                'extra_input': 'relationship_user: "{huser_id}"'
                                    .format(huser_id=huser_id),
                'extra_query': '''
                    host_user {
                      id
                      name
                    }
                ''',
                'check_path': lambda x: x['host_user']['id'],
                'id': huser_id,
            },
            'physical':{
                'extra_input': 'relationship_owner: "{owner_id}"'
                                    .format(owner_id=owner_id),
                'extra_query': '''
                    host_owner {
                      id
                      name
                    }
                ''',
                'check_path': lambda x: x['host_owner']['id'],
                'id': owner_id,
            }
        }

        use_ownerhuser = True

        updated_hosts = {
            'logical': None,
            'physical': None,
        }

        for iteration in range(0,2):
            for k, host_id in host_ids.items():
                host_name = community_generator.fake.hostname()
                host_description = community_generator.fake.paragraph()

                ip_adresses = [
                    community_generator.fake.ipv4(),
                    community_generator.fake.ipv4(),
                ]

                rack_units = random.randint(1,10)
                rack_position = random.randint(1,10)
                rack_back = bool(random.getrandbits(1))

                operational_state = random.choice(
                    Dropdown.objects.get(name="operational_states")\
                        .as_choices()[1:][1]
                )

                managed_by = random.choice(
                    Dropdown.objects.get(name="host_management_sw")\
                        .as_choices()[1:][1]
                )
                backup = "Automatic script"
                os = "GNU/Linux"
                os_version = "Debian"
                contract_number = "002"

                check_id_value = host_user_query[k]['id']
                extra_input = host_user_query[k]['extra_input']
                extra_query = host_user_query[k]['extra_query']

                # in the first iteration we'll set a different host user / owner
                # in the second iteration these will be set to none
                if not use_ownerhuser:
                    check_id_value = None
                    extra_input = ''
                    extra_query = host_user_query[k]['extra_query']

                services_locked = bool(random.getrandbits(1))

                query = edit_query.format(
                            host_id=host_id,
                            host_name=host_name, host_description=host_description,
                            ip_address="\\n".join(ip_addresses),
                            rack_units=rack_units, rack_position=rack_position,
                            rack_back=str(rack_back).lower(),
                            operational_state=operational_state,
                            group1_id=group1_id, group2_id=group2_id,
                            managed_by=managed_by, backup=backup, os=os,
                            os_version=os_version, contract_number=contract_number,
                            services_locked=str(services_locked).lower(),
                            extra_input=extra_input, extra_query=extra_query,
                            subinputs='', subquery='')

                result = schema.execute(query, context=self.context)
                assert not result.errors, pformat(result.errors, indent=1)

                # check for errors
                created_errors = result.data['composite_host']['updated']['errors']
                assert not created_errors, pformat(created_errors, indent=1)

                # check data
                updated_host = result.data['composite_host']['updated']['host']
                updated_hosts[k] = updated_host

                self.assertEqual(updated_host['name'], host_name)
                self.assertEqual(updated_host['description'], host_description)
                self.assertEqual(updated_host['operational_state']['value'], operational_state)
                self.assertEqual(updated_host['rack_units'], rack_units)
                self.assertEqual(updated_host['rack_position'], rack_position)
                self.assertEqual(updated_host['rack_back'], rack_back)
                self.assertEqual(updated_host['ip_addresses'], ip_addresses)
                self.assertEqual(updated_host['managed_by']['value'], managed_by)
                self.assertEqual(updated_host['backup'], backup)
                self.assertEqual(updated_host['os'], os)
                self.assertEqual(updated_host['os_version'], os_version)
                self.assertEqual(updated_host['contract_number'], contract_number)
                self.assertEqual(updated_host['services_locked'], services_locked)

                check_id = None

                if use_ownerhuser:
                    check_id = host_user_query[k]['check_path'](updated_host)

                self.assertEqual(check_id_value, check_id)

                # check responsible group
                check_responsible = updated_host['responsible_group']
                self.assertEqual(check_responsible['id'], group1_id)

                # check support group
                check_support = updated_host['support_group']
                self.assertEqual(check_support['id'], group2_id)

                use_ownerhuser = False

        # add a port to a physical host
        # and check that's not possible with a logical host
        generator = NetworkFakeDataGenerator()

        for k, host_id in host_ids.items():
            # get old values
            host_name = updated_hosts[k]['name']
            host_description = updated_hosts[k]['name']
            ip_addresses = updated_hosts[k]['ip_addresses']
            rack_units = updated_hosts[k]['rack_units']
            rack_position = updated_hosts[k]['rack_position']
            rack_back = updated_hosts[k]['rack_back']
            operational_state = updated_hosts[k]['operational_state']['value']
            rack_back = updated_hosts[k]['rack_back']
            managed_by = updated_hosts[k]['managed_by']['value']
            backup = updated_hosts[k]['backup']
            os = updated_hosts[k]['os']
            os_version = updated_hosts[k]['os_version']
            contract_number = updated_hosts[k]['contract_number']
            services_locked = updated_hosts[k]['services_locked']

            # create new port
            port_1_name = str(random.randint(0, 50000))
            port_1_type = random.choice(
                Dropdown.objects.get(name="port_types").as_choices()[1:][1]
            )
            port_1_description = generator\
                                    .escape_quotes(generator.fake.paragraph())

            # add existent port
            port = generator.create_port()
            port_2_id = relay.Node.to_global_id(str(port.node_type),
                                                str(port.handle_id))
            port_2_name = str(random.randint(0, 50000))
            port_2_type = random.choice(
                Dropdown.objects.get(name="port_types").as_choices()[1:][1]
            )
            port_2_description = generator\
                                    .escape_quotes(generator.fake.paragraph())

            # count ports present on db to be checked after
            num_ports = NodeHandle.objects\
                            .filter(node_type=port.node_type).count()

            subinput = '''
            create_subinputs:[
              {{
                name: "{port_1_name}"
                port_type: "{port_1_type}"
                description: "{port_1_description}"
              }}
            ]
            update_subinputs:[
              {{
                id: "{port_2_id}"
                name: "{port_2_name}"
                port_type: "{port_2_type}"
                description: "{port_2_description}"
              }}
            ]
            '''.format(
                port_1_name=port_1_name, port_1_type=port_1_type,
                port_1_description=port_1_description, port_2_id=port_2_id,
                port_2_name=port_2_name, port_2_type=port_2_type,
                port_2_description=port_2_description
            )

            subquery = '''
            subcreated{
              errors{
                field
                messages
              }
              port{
                id
                name
                port_type{
                  name
                  value
                }
                description
                parent{
                  id
                  name
                }
              }
            }
            subupdated{
              errors{
                field
                messages
              }
              port{
                id
                name
                port_type{
                  name
                  value
                }
                description
                parent{
                  id
                  name
                }
              }
            }
            '''

            query = edit_query.format(
                        host_id=host_id,
                        host_name=host_name, host_description=host_description,
                        ip_address="\\n".join(ip_addresses),
                        rack_units=rack_units, rack_position=rack_units,
                        rack_back=str(rack_back).lower(),
                        operational_state=operational_state,
                        group1_id=group1_id, group2_id=group2_id,
                        managed_by=managed_by, backup=backup, os=os,
                        os_version=os_version, contract_number=contract_number,
                        services_locked=str(services_locked).lower(),
                        extra_input='', extra_query='',
                        subinputs=subinput, subquery=subquery)

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            # check for errors
            created_errors = result.data['composite_host']['updated']['errors']
            assert not created_errors, pformat(created_errors, indent=1)

            if k == 'logical':
                # check that ports are not created
                new_num_ports = NodeHandle.objects\
                                .filter(node_type=port.node_type).count()
                self.assertEquals(num_ports, new_num_ports)
            else:
                # check port_1 data
                created_checkport = result.data['composite_host']['subcreated'][0]
                created_errors = created_checkport['errors']
                assert not created_errors, pformat(created_errors, indent=1)

                created_checkport = created_checkport['port']
                port_1_id = created_checkport['id']

                self.assertEqual(created_checkport['name'], port_1_name)
                self.assertEqual(created_checkport['port_type']['value'], port_1_type)
                self.assertEqual(created_checkport['description'], port_1_description)

                # check port_2
                update_checkport = result.data['composite_host']['subupdated'][0]
                updated_errors = update_checkport['errors']
                assert not updated_errors, pformat(updated_errors, indent=1)

                update_checkport = update_checkport['port']
                self.assertEqual(update_checkport['name'], port_2_name)
                self.assertEqual(update_checkport['port_type']['value'], port_2_type)
                self.assertEqual(update_checkport['description'], port_2_description)


class OpticalNodeTest(Neo4jGraphQLNetworkTest):
    def test_optical_node(self):
        # optical node data
        optno_name = "Optical Node test"
        optno_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = 2
        rack_position = 3
        rack_back = bool(random.getrandbits(1))

        optno_type = random.choice(
            Dropdown.objects.get(name="optical_node_types").as_choices()[1:])[1]

        optno_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        # port data
        port1_name = "test-01"
        port1_type = "Schuko"
        port1_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        # generate second port
        net_generator = NetworkFakeDataGenerator()
        port2 = net_generator.create_port()
        port2_name = port2.node_name
        port2_description = port2.get_node().data.get('description')
        port2_type = port2.get_node().data.get('port_type')
        port2_id = relay.Node.to_global_id(str(port2.node_type),
                                            str(port2.handle_id))

        # get a location
        location = net_generator.create_rack()
        location_id = relay.Node.to_global_id(str(location.node_type),
                                                str(location.handle_id))

        query = '''
        mutation{{
          composite_opticalNode(input:{{
            create_input:{{
              name: "{optno_name}"
              description: "{optno_description}"
              type: "{optno_type}"
              operational_state: "{optno_opstate}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
              relationship_location: "{location_id}"
            }}
            create_has_port:[
              {{
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
          	update_has_port:[
              {{
                id: "{port2_id}"
                name: "{port2_name}"
                description: "{port2_description}"
                port_type: "{port2_type}"
              }},
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              opticalNode{{
                id
                name
                description
                type{{
                  id
                  value
                }}
                operational_state{{
                  id
                  value
                }}
                rack_units
                rack_position
                rack_back
                has{{
                  id
                  name
                }}
                ports{{
                  id
                  name
                }}
                location{{
                  id
                  name
                }}
              }}
            }}
            has_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
          }}
        }}
        '''.format(optno_name=optno_name, optno_description=optno_description,
                    optno_type=optno_type, optno_opstate=optno_opstate,
                    rack_units=rack_units, rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port1_name=port1_name, port1_type=port1_type,
                    port1_description=port1_description, port2_id=port2_id,
                    port2_name=port2_name, port2_type=port2_type,
                    port2_description=port2_description,
                    location_id=location_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = \
            result.data['composite_opticalNode']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        subcreated_errors = \
            result.data['composite_opticalNode']['has_port_created'][0]['errors']
        assert not subcreated_errors, pformat(subcreated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_opticalNode']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        # check data
        created_optnode = result.data['composite_opticalNode']['created']\
            ['opticalNode']
        optno_id = created_optnode['id']

        self.assertEqual(created_optnode['name'], optno_name)
        self.assertEqual(created_optnode['description'], optno_description)
        self.assertEqual(created_optnode['type']['value'], optno_type)
        self.assertEqual(created_optnode['operational_state']['value'],
                            optno_opstate)
        self.assertEqual(created_optnode['rack_units'], rack_units)
        self.assertEqual(created_optnode['rack_position'], rack_position)
        self.assertEqual(created_optnode['rack_back'], rack_back)

        # check subentities
        port1_id = result.data \
            ['composite_opticalNode']['has_port_created'][0]['port']['id']
        check_port1 = result.data \
            ['composite_opticalNode']['has_port_created'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_port2 = result.data \
            ['composite_opticalNode']['has_port_updated'][0]['port']

        self.assertEqual(check_port2['id'], port2_id)
        self.assertEqual(check_port2['name'], port2_name)
        self.assertEqual(check_port2['description'], port2_description)
        self.assertEqual(check_port2['port_type']['value'], port2_type)

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in created_optnode['ports']]

        self.assertTrue(port1_id in has_ids)
        self.assertTrue(port2_id in has_ids)

        # check location
        check_location = created_optnode['location']
        self.assertEqual(check_location['id'], location_id)

        # update query
        optno_name = "Optical Node check"
        optno_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = 3
        rack_position = 2
        rack_back = bool(random.getrandbits(1))

        optno_type = random.choice(
            Dropdown.objects.get(name="optical_node_types").as_choices()[1:])[1]

        optno_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        port1_name = "check-01"
        port1_type = port2_type
        port1_description = port2_description

        query = '''
        mutation{{
          composite_opticalNode(input:{{
            update_input:{{
              id: "{optno_id}"
              name: "{optno_name}"
              description: "{optno_description}"
              type: "{optno_type}"
              operational_state: "{optno_opstate}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
            }}
          	update_has_port:[
              {{
                id: "{port1_id}"
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
            deleted_has_port:[
              {{
                id: "{port2_id}"
              }}
          	]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              opticalNode{{
                id
                name
                description
                type{{
                  id
                  value
                }}
                operational_state{{
                  id
                  value
                }}
                rack_units
                rack_position
                rack_back
                has{{
                  id
                  name
                }}
                ports{{
                  id
                  name
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_deleted{{
              errors{{
                field
                messages
              }}
              success
            }}
          }}
        }}
        '''.format(optno_id=optno_id, optno_name=optno_name,
                    optno_description=optno_description, optno_type=optno_type,
                    optno_opstate=optno_opstate, rack_units=rack_units,
                    rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port1_id=port1_id, port1_name=port1_name,
                    port1_type=port1_type, port1_description=port1_description,
                    port2_id=port2_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = \
            result.data['composite_opticalNode']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_opticalNode']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        subdeleted_errors = \
            result.data['composite_opticalNode']['has_port_deleted'][0]['errors']
        assert not subdeleted_errors, pformat(subdeleted_errors, indent=1)

        # check data
        updated_optnode = result.data['composite_opticalNode']['updated']['opticalNode']
        self.assertEqual(updated_optnode['name'], optno_name)
        self.assertEqual(updated_optnode['description'], optno_description)
        self.assertEqual(updated_optnode['type']['value'], optno_type)
        self.assertEqual(updated_optnode['operational_state']['value'],
                            optno_opstate)
        self.assertEqual(updated_optnode['rack_units'], rack_units)
        self.assertEqual(updated_optnode['rack_position'], rack_position)
        self.assertEqual(updated_optnode['rack_back'], rack_back)

        # check subentities
        check_port1 = result.data \
            ['composite_opticalNode']['has_port_updated'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_deleted_port2 = result.data \
            ['composite_opticalNode']['has_port_deleted'][0]['success']

        self.assertTrue(check_deleted_port2)

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in updated_optnode['ports']]

        self.assertTrue(port1_id in has_ids)
        self.assertFalse(port2_id in has_ids)


class ODFTest(Neo4jGraphQLNetworkTest):
    def test_odf(self):
        # odf data
        odf_name = "ODF test"
        odf_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = random.randint(1, 3)
        rack_position = random.randint(1, 5)
        rack_back = bool(random.getrandbits(1))

        odf_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        # port data
        port1_name = "test-01"
        port1_type = "Schuko"
        port1_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        # generate second port
        net_generator = NetworkFakeDataGenerator()
        port2 = net_generator.create_port()
        port2_name = port2.node_name
        port2_description = port2.get_node().data.get('description')
        port2_type = port2.get_node().data.get('port_type')
        port2_id = relay.Node.to_global_id(str(port2.node_type),
                                            str(port2.handle_id))

        # get a location
        location = net_generator.create_rack()
        location_id = relay.Node.to_global_id(str(location.node_type),
                                                str(location.handle_id))

        query = '''
        mutation{{
          composite_oDF(input:{{
            create_input:{{
              name: "{odf_name}"
              description: "{odf_description}"
              operational_state: "{odf_opstate}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
              relationship_location: "{location_id}"
            }}
            create_has_port:[
              {{
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
          	update_has_port:[
              {{
                id: "{port2_id}"
                name: "{port2_name}"
                description: "{port2_description}"
                port_type: "{port2_type}"
              }},
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              oDF{{
                id
                name
                description
                operational_state{{
                  id
                  value
                }}
                rack_units
                rack_position
                rack_back
                has{{
                  id
                  name
                }}
                ports{{
                  id
                  name
                }}
                location{{
                  id
                  name
                }}
              }}
            }}
            has_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
          }}
        }}
        '''.format(odf_name=odf_name, odf_description=odf_description,
                    odf_opstate=odf_opstate, rack_units=rack_units,
                    rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port1_name=port1_name, port1_type=port1_type,
                    port1_description=port1_description, port2_id=port2_id,
                    port2_name=port2_name, port2_type=port2_type,
                    port2_description=port2_description,
                    location_id=location_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = \
            result.data['composite_oDF']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        subcreated_errors = \
            result.data['composite_oDF']['has_port_created'][0]['errors']
        assert not subcreated_errors, pformat(subcreated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_oDF']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        # check data
        created_odf = result.data['composite_oDF']['created']\
            ['oDF']
        odf_id = created_odf['id']

        self.assertEqual(created_odf['name'], odf_name)
        self.assertEqual(created_odf['description'], odf_description)
        self.assertEqual(created_odf['operational_state']['value'],
                            odf_opstate)
        self.assertEqual(created_odf['rack_units'], rack_units)
        self.assertEqual(created_odf['rack_position'], rack_position)
        self.assertEqual(created_odf['rack_back'], rack_back)

        # check subentities
        port1_id = result.data \
            ['composite_oDF']['has_port_created'][0]['port']['id']
        check_port1 = result.data \
            ['composite_oDF']['has_port_created'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_port2 = result.data \
            ['composite_oDF']['has_port_updated'][0]['port']

        self.assertEqual(check_port2['id'], port2_id)
        self.assertEqual(check_port2['name'], port2_name)
        self.assertEqual(check_port2['description'], port2_description)
        self.assertEqual(check_port2['port_type']['value'], port2_type)

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in created_odf['ports']]

        self.assertTrue(port1_id in has_ids)
        self.assertTrue(port2_id in has_ids)

        # check location
        check_location = created_odf['location']
        self.assertEqual(check_location['id'], location_id)

        # update query
        odf_name = "Optical Node check"
        odf_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = 3
        rack_position = 2
        rack_back = bool(random.getrandbits(1))

        odf_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        port1_name = "check-01"
        port1_type = port2_type
        port1_description = port2_description

        query = '''
        mutation{{
          composite_oDF(input:{{
            update_input:{{
              id: "{odf_id}"
              name: "{odf_name}"
              description: "{odf_description}"
              operational_state: "{odf_opstate}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
            }}
          	update_has_port:[
              {{
                id: "{port1_id}"
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
            deleted_has_port:[
              {{
                id: "{port2_id}"
              }}
          	]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              oDF{{
                id
                name
                description
                operational_state{{
                  id
                  value
                }}
                rack_units
                rack_position
                rack_back
                has{{
                  id
                  name
                }}
                ports{{
                  id
                  name
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_deleted{{
              errors{{
                field
                messages
              }}
              success
            }}
          }}
        }}
        '''.format(odf_id=odf_id, odf_name=odf_name,
                    odf_description=odf_description,
                    odf_opstate=odf_opstate, rack_units=rack_units,
                    rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port1_id=port1_id, port1_name=port1_name,
                    port1_type=port1_type, port1_description=port1_description,
                    port2_id=port2_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = \
            result.data['composite_oDF']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_oDF']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        subdeleted_errors = \
            result.data['composite_oDF']['has_port_deleted'][0]['errors']
        assert not subdeleted_errors, pformat(subdeleted_errors, indent=1)

        # check data
        updated_odf = result.data['composite_oDF']['updated']['oDF']
        self.assertEqual(updated_odf['name'], odf_name)
        self.assertEqual(updated_odf['description'], odf_description)
        self.assertEqual(updated_odf['operational_state']['value'],
                            odf_opstate)
        self.assertEqual(updated_odf['rack_units'], rack_units)
        self.assertEqual(updated_odf['rack_position'], rack_position)
        self.assertEqual(updated_odf['rack_back'], rack_back)

        # check subentities
        check_port1 = result.data \
            ['composite_oDF']['has_port_updated'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_deleted_port2 = result.data \
            ['composite_oDF']['has_port_deleted'][0]['success']

        self.assertTrue(check_deleted_port2)

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in updated_odf['ports']]

        self.assertTrue(port1_id in has_ids)
        self.assertFalse(port2_id in has_ids)


## Optical Nodes
class OpticalFilterTest(Neo4jGraphQLNetworkTest):
    def test_optical_filter(self):
        # optical filter data
        ofilter_name = "Optical filter test"
        ofilter_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = random.randint(1, 3)
        rack_position = random.randint(1, 5)
        rack_back = bool(random.getrandbits(1))

        ofilter_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        # port data
        port1_name = "test-01"
        port1_type = "Schuko"
        port1_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        # generate second port
        net_generator = NetworkFakeDataGenerator()
        port2 = net_generator.create_port()
        port2_name = port2.node_name
        port2_description = port2.get_node().data.get('description')
        port2_type = port2.get_node().data.get('port_type')
        port2_id = relay.Node.to_global_id(str(port2.node_type),
                                            str(port2.handle_id))

        # get a location
        location = net_generator.create_rack()
        location_id = relay.Node.to_global_id(str(location.node_type),
                                                str(location.handle_id))

        query = '''
        mutation{{
          composite_opticalFilter(input:{{
            create_input:{{
              name: "{ofilter_name}"
              description: "{ofilter_description}"
              operational_state: "{ofilter_opstate}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
              relationship_location: "{location_id}"
            }}
            create_has_port:[
              {{
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
          	update_has_port:[
              {{
                id: "{port2_id}"
                name: "{port2_name}"
                description: "{port2_description}"
                port_type: "{port2_type}"
              }},
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              opticalFilter{{
                id
                name
                description
                operational_state{{
                  id
                  value
                }}
                rack_units
                rack_position
                rack_back
                has{{
                  id
                  name
                }}
                ports{{
                  id
                  name
                }}
                location{{
                  id
                  name
                }}
              }}
            }}
            has_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
          }}
        }}
        '''.format(ofilter_name=ofilter_name, ofilter_description=ofilter_description,
                    ofilter_opstate=ofilter_opstate, rack_units=rack_units,
                    rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port1_name=port1_name, port1_type=port1_type,
                    port1_description=port1_description, port2_id=port2_id,
                    port2_name=port2_name, port2_type=port2_type,
                    port2_description=port2_description,
                    location_id=location_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = \
            result.data['composite_opticalFilter']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        subcreated_errors = \
            result.data['composite_opticalFilter']['has_port_created'][0]['errors']
        assert not subcreated_errors, pformat(subcreated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_opticalFilter']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        # check data
        created_ofilter = result.data['composite_opticalFilter']['created']\
            ['opticalFilter']
        ofilter_id = created_ofilter['id']

        self.assertEqual(created_ofilter['name'], ofilter_name)
        self.assertEqual(created_ofilter['description'], ofilter_description)
        self.assertEqual(created_ofilter['operational_state']['value'],
                            ofilter_opstate)
        self.assertEqual(created_ofilter['rack_units'], rack_units)
        self.assertEqual(created_ofilter['rack_position'], rack_position)
        self.assertEqual(created_ofilter['rack_back'], rack_back)

        # check subentities
        port1_id = result.data \
            ['composite_opticalFilter']['has_port_created'][0]['port']['id']
        check_port1 = result.data \
            ['composite_opticalFilter']['has_port_created'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_port2 = result.data \
            ['composite_opticalFilter']['has_port_updated'][0]['port']

        self.assertEqual(check_port2['id'], port2_id)
        self.assertEqual(check_port2['name'], port2_name)
        self.assertEqual(check_port2['description'], port2_description)
        self.assertEqual(check_port2['port_type']['value'], port2_type)

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in created_ofilter['ports']]

        self.assertTrue(port1_id in has_ids)
        self.assertTrue(port2_id in has_ids)

        # check location
        check_location = created_ofilter['location']
        self.assertEqual(check_location['id'], location_id)

        # update query
        ofilter_name = "Optical Node check"
        ofilter_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        rack_units = 3
        rack_position = 2
        rack_back = bool(random.getrandbits(1))

        ofilter_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        port1_name = "check-01"
        port1_type = port2_type
        port1_description = port2_description

        query = '''
        mutation{{
          composite_opticalFilter(input:{{
            update_input:{{
              id: "{ofilter_id}"
              name: "{ofilter_name}"
              description: "{ofilter_description}"
              operational_state: "{ofilter_opstate}"
              rack_units: {rack_units}
              rack_position: {rack_position}
              rack_back: {rack_back}
            }}
          	update_has_port:[
              {{
                id: "{port1_id}"
                name: "{port1_name}"
                description: "{port1_description}"
                port_type: "{port1_type}"
              }},
            ]
            deleted_has_port:[
              {{
                id: "{port2_id}"
              }}
          	]
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              opticalFilter{{
                id
                name
                description
                operational_state{{
                  id
                  value
                }}
                rack_units
                rack_position
                rack_back
                has{{
                  id
                  name
                }}
                ports{{
                  id
                  name
                }}
              }}
            }}
            has_port_updated{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                description
                port_type{{
                  id
                  value
                }}
              }}
            }}
            has_port_deleted{{
              errors{{
                field
                messages
              }}
              success
            }}
          }}
        }}
        '''.format(ofilter_id=ofilter_id, ofilter_name=ofilter_name,
                    ofilter_description=ofilter_description,
                    ofilter_opstate=ofilter_opstate, rack_units=rack_units,
                    rack_position=rack_position,
                    rack_back=str(rack_back).lower(),
                    port1_id=port1_id, port1_name=port1_name,
                    port1_type=port1_type, port1_description=port1_description,
                    port2_id=port2_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = \
            result.data['composite_opticalFilter']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_opticalFilter']['has_port_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        subdeleted_errors = \
            result.data['composite_opticalFilter']['has_port_deleted'][0]['errors']
        assert not subdeleted_errors, pformat(subdeleted_errors, indent=1)

        # check data
        updated_ofilter = result.data['composite_opticalFilter']['updated']['opticalFilter']
        self.assertEqual(updated_ofilter['name'], ofilter_name)
        self.assertEqual(updated_ofilter['description'], ofilter_description)
        self.assertEqual(updated_ofilter['operational_state']['value'],
                            ofilter_opstate)
        self.assertEqual(updated_ofilter['rack_units'], rack_units)
        self.assertEqual(updated_ofilter['rack_position'], rack_position)
        self.assertEqual(updated_ofilter['rack_back'], rack_back)

        # check subentities
        check_port1 = result.data \
            ['composite_opticalFilter']['has_port_updated'][0]['port']

        self.assertEqual(check_port1['name'], port1_name)
        self.assertEqual(check_port1['description'], port1_description)
        self.assertEqual(check_port1['port_type']['value'], port1_type)

        check_deleted_port2 = result.data \
            ['composite_opticalFilter']['has_port_deleted'][0]['success']

        self.assertTrue(check_deleted_port2)

        # check that the ports are related to the equipment
        has_ids = [x['id'] for x in updated_ofilter['ports']]

        self.assertTrue(port1_id in has_ids)
        self.assertFalse(port2_id in has_ids)


class OpticalLinkTest(Neo4jGraphQLNetworkTest):
    def test_optical_link(self):
        olink_name = "Optical Link Test"
        olink_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."

        olink_linktype = random.choice(
            Dropdown.objects.get(name="optical_link_types").as_choices()[1:])[1]

        olink_ifacetype = random.choice(
            Dropdown.objects.get(name="optical_link_interface_type").as_choices()[1:])[1]

        olink_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        aport_name = "test-01"
        aport_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
        aport_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        bport_name = "test-02"
        bport_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
        bport_description = "Nunc varius suscipit lorem, non posuere nisl "\
            "consequat in. Nulla gravida sapien a velit aliquet, aliquam "\
            "tincidunt urna ultrices. Vivamus venenatis ligula a erat "\
            "fringilla faucibus. Suspendisse potenti. Donec rutrum eget "\
            "nunc sed volutpat. Curabitur sit amet lorem elementum sapien "\
            "ornare placerat."

        # set a provider
        generator = NetworkFakeDataGenerator()
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # Create query
        query = '''
        mutation{{
          composite_opticalLink(input:{{
            create_input:{{
              name: "{olink_name}"
              description: "{olink_description}"
              link_type: "{olink_linktype}"
              interface_type: "{olink_ifacetype}"
              operational_state: "{olink_opstate}"
              relationship_provider: "{provider_id}"
            }}
            create_dependencies_port:[
              {{
                name: "{aport_name}"
                port_type: "{aport_type}"
                description: "{aport_description}"
              }},
              {{
                name: "{bport_name}"
                port_type: "{bport_type}"
                description: "{bport_description}"
              }}
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              opticalLink{{
                id
                name
                description
                link_type{{
                  value
                }}
                interface_type{{
                  value
                }}
                operational_state{{
                  value
                }}
                ports{{
                  id
                  name
                  port_type{{
                    value
                  }}
                  description
                }}
                provider{{
                  id
                  name
                }}
              }}
            }}
            dependencies_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  value
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(olink_name=olink_name, olink_description=olink_description,
                    olink_linktype=olink_linktype,
                    olink_ifacetype=olink_ifacetype,
                    olink_opstate=olink_opstate, aport_name=aport_name,
                    aport_type=aport_type, aport_description=aport_description,
                    bport_name=bport_name, bport_type=bport_type,
                    bport_description=bport_description, provider_id=provider_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_opticalLink']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_opticalLink']\
                                    ['dependencies_port_created']:
            assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

        # get the ids
        result_data = result.data['composite_opticalLink']
        olink_id = result_data['created']['opticalLink']['id']
        aport_id = result_data['dependencies_port_created'][0]['port']['id']
        bport_id = result_data['dependencies_port_created'][1]['port']['id']

        # check the integrity of the data
        created_data = result_data['created']['opticalLink']

        # check main optical link
        self.assertEqual(created_data['name'], olink_name)
        self.assertEqual(created_data['description'], olink_description)
        self.assertEqual(created_data['link_type']['value'], olink_linktype)
        self.assertEqual(created_data['interface_type']['value'], olink_ifacetype)
        self.assertEqual(created_data['operational_state']['value'], olink_opstate)

        # check their relations id
        test_aport_id = created_data['ports'][0]['id']
        test_bport_id = created_data['ports'][1]['id']

        self.assertEqual(aport_id, test_aport_id)
        self.assertEqual(bport_id, test_bport_id)

        # check ports in both payload and metatype attribute
        check_aports = [
            created_data['ports'][0],
            result_data['dependencies_port_created'][0]['port'],
        ]

        for check_aport in check_aports:
            self.assertEqual(check_aport['name'], aport_name)
            self.assertEqual(check_aport['port_type']['value'], aport_type)
            self.assertEqual(check_aport['description'], aport_description)

        check_bports = [
            created_data['ports'][1],
            result_data['dependencies_port_created'][1]['port'],
        ]

        for check_bport in check_bports:
            self.assertEqual(check_bport['name'], bport_name)
            self.assertEqual(check_bport['port_type']['value'], bport_type)
            self.assertEqual(check_bport['description'], bport_description)

        # check provider
        check_provider = result_data['created']['opticalLink']['provider']
        self.assertEqual(check_provider['id'], provider_id)
        self.assertEqual(check_provider['name'], provider.node_name)

        ## Update query
        # (do it two times to check that the relationship id is not overwritten)
        relation_id = None
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        for i in range(2):
            buffer_description = olink_description
            buffer_description2 = aport_description

            olink_name = "New Optical Link"
            olink_description = bport_description

            olink_linktype = random.choice(
                Dropdown.objects.get(name="optical_link_types").as_choices()[1:])[1]

            olink_ifacetype = random.choice(
                Dropdown.objects.get(name="optical_link_interface_type").as_choices()[1:])[1]

            olink_opstate = random.choice(
                Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

            aport_name = "port-01"
            aport_type = random.choice(
                Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
            aport_description = buffer_description2

            bport_name = "port-02"
            bport_type = random.choice(
                Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
            bport_description = buffer_description

            query = '''
            mutation{{
              composite_opticalLink(input:{{
                update_input:{{
                  id: "{olink_id}"
                  name: "{olink_name}"
                  description: "{olink_description}"
                  link_type: "{olink_linktype}"
                  interface_type: "{olink_ifacetype}"
                  operational_state: "{olink_opstate}"
                  relationship_provider: "{provider_id}"
                }}
                update_dependencies_port:[
                  {{
                    id: "{aport_id}"
                    name: "{aport_name}"
                    port_type: "{aport_type}"
                    description: "{aport_description}"
                  }},
                  {{
                    id: "{bport_id}"
                    name: "{bport_name}"
                    port_type: "{bport_type}"
                    description: "{bport_description}"
                  }}
                ]
              }}){{
                updated{{
                  errors{{
                    field
                    messages
                  }}
                  opticalLink{{
                    id
                    name
                    description
                    link_type{{
                      value
                    }}
                    interface_type{{
                      value
                    }}
                    operational_state{{
                      value
                    }}
                    ports{{
                      id
                      name
                      port_type{{
                        value
                      }}
                      description
                    }}
                    provider{{
                      id
                      name
                      relation_id
                    }}
                  }}
                }}
                dependencies_port_updated{{
                  errors{{
                    field
                    messages
                  }}
                  port{{
                    id
                    name
                    port_type{{
                      value
                    }}
                    description
                  }}
                }}
              }}
            }}
            '''.format(olink_name=olink_name, olink_description=olink_description,
                        olink_linktype=olink_linktype,
                        olink_ifacetype=olink_ifacetype,
                        olink_opstate=olink_opstate, aport_name=aport_name,
                        aport_type=aport_type, aport_description=aport_description,
                        bport_name=bport_name, bport_type=bport_type,
                        bport_description=bport_description, olink_id=olink_id,
                        aport_id=aport_id, bport_id=bport_id, provider_id=provider_id)

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            # check for errors
            created_errors = result.data['composite_opticalLink']['updated']['errors']
            assert not created_errors, pformat(created_errors, indent=1)

            for subcreated in result.data['composite_opticalLink']['dependencies_port_updated']:
                assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

            # check the integrity of the data
            result_data = result.data['composite_opticalLink']
            updated_data = result_data['updated']['opticalLink']

            # check main optical link
            self.assertEqual(updated_data['name'], olink_name)
            self.assertEqual(updated_data['description'], olink_description)
            self.assertEqual(updated_data['link_type']['value'], olink_linktype)
            self.assertEqual(updated_data['interface_type']['value'], olink_ifacetype)
            self.assertEqual(updated_data['operational_state']['value'], olink_opstate)

            # check their relations id
            test_aport_id = updated_data['ports'][0]['id']
            test_bport_id = updated_data['ports'][1]['id']

            self.assertEqual(aport_id, test_aport_id)
            self.assertEqual(bport_id, test_bport_id)

            # check ports in both payload and metatype attribute
            check_aports = [
                updated_data['ports'][0],
                result_data['dependencies_port_updated'][0]['port'],
            ]

            for check_aport in check_aports:
                self.assertEqual(check_aport['name'], aport_name)
                self.assertEqual(check_aport['port_type']['value'], aport_type)
                self.assertEqual(check_aport['description'], aport_description)

            check_bports = [
                updated_data['ports'][1],
                result_data['dependencies_port_updated'][1]['port'],
            ]

            for check_bport in check_bports:
                self.assertEqual(check_bport['name'], bport_name)
                self.assertEqual(check_bport['port_type']['value'], bport_type)
                self.assertEqual(check_bport['description'], bport_description)

            # check provider
            check_provider = result_data['updated']['opticalLink']['provider']
            self.assertEqual(check_provider['id'], provider_id)
            self.assertEqual(check_provider['name'], provider.node_name)

            # check that we only have one provider
            _type, olink_handle_id = relay.Node.from_global_id(olink_id)
            olink_nh = NodeHandle.objects.get(handle_id=olink_handle_id)
            olink_node = olink_nh.get_node()
            previous_rels = olink_node.incoming.get('Provides', [])
            self.assertTrue(len(previous_rels) == 1)

            # check relation_id
            if not relation_id: # first run
                relation_id = check_provider['relation_id']
                self.assertIsNotNone(relation_id)
            else:
                self.assertEqual(relation_id, check_provider['relation_id'])

        ## Update query 2 (remove provider)
        query = '''
        mutation{{
          composite_opticalLink(input:{{
            update_input:{{
              id: "{olink_id}"
              name: "{olink_name}"
              description: "{olink_description}"
              link_type: "{olink_linktype}"
              interface_type: "{olink_ifacetype}"
              operational_state: "{olink_opstate}"
            }}
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              opticalLink{{
                id
                name
                description
                link_type{{
                  value
                }}
                interface_type{{
                  value
                }}
                operational_state{{
                  value
                }}
                provider{{
                  id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(olink_id=olink_id, olink_name=olink_name,
                    olink_description=olink_description,
                    olink_linktype=olink_linktype,
                    olink_ifacetype=olink_ifacetype,
                    olink_opstate=olink_opstate)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_opticalLink']['updated']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        # check empty provider
        check_provider = result.data['composite_opticalLink']['updated']['opticalLink']['provider']
        self.assertEqual(check_provider, None)


class OpticalMultiplexSectionTest(Neo4jGraphQLNetworkTest):
    def test_optical_multiplex(self):
        oms23_name = "Optical Multiplex Section Test"
        oms23_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."

        oms23_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        aport_name = "test-01"
        aport_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
        aport_description = "Etiam non libero pharetra, ultrices nunc ut, "\
            "finibus ante. Suspendisse potenti. Nulla facilisi. Maecenas et "\
            "pretium risus, non porta nunc. Sed id sem tempus, condimentum "\
            "quam mattis, venenatis metus. Nullam lobortis leo mi, vel "\
            "elementum neque maximus in. Cras non lectus at lorem consectetur "\
            "euismod."

        bport_name = "test-02"
        bport_type = random.choice(
            Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
        bport_description = "Nunc varius suscipit lorem, non posuere nisl "\
            "consequat in. Nulla gravida sapien a velit aliquet, aliquam "\
            "tincidunt urna ultrices. Vivamus venenatis ligula a erat "\
            "fringilla faucibus. Suspendisse potenti. Donec rutrum eget "\
            "nunc sed volutpat. Curabitur sit amet lorem elementum sapien "\
            "ornare placerat."

        # set a provider
        generator = NetworkFakeDataGenerator()
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # Create query
        query = '''
        mutation{{
          composite_opticalMultiplexSection(input:{{
            create_input:{{
              name: "{oms23_name}"
              description: "{oms23_description}"
              operational_state: "{oms23_opstate}"
              relationship_provider: "{provider_id}"
            }}
            create_dependencies_port:[
              {{
                name: "{aport_name}"
                port_type: "{aport_type}"
                description: "{aport_description}"
              }},
              {{
                name: "{bport_name}"
                port_type: "{bport_type}"
                description: "{bport_description}"
              }}
            ]
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              opticalMultiplexSection{{
                id
                name
                description
                operational_state{{
                  value
                }}
                dependencies{{
                  id
                  name
                  ...on Port{{
                    port_type{{
                      value
                    }}
                    description
                  }}
                }}
                provider{{
                  id
                  name
                }}
              }}
            }}
            dependencies_port_created{{
              errors{{
                field
                messages
              }}
              port{{
                id
                name
                port_type{{
                  value
                }}
                description
              }}
            }}
          }}
        }}
        '''.format(oms23_name=oms23_name, oms23_description=oms23_description,
                    oms23_opstate=oms23_opstate, aport_name=aport_name,
                    aport_type=aport_type, aport_description=aport_description,
                    bport_name=bport_name, bport_type=bport_type,
                    bport_description=bport_description, provider_id=provider_id)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_opticalMultiplexSection']\
                                        ['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_opticalMultiplexSection']\
                                    ['dependencies_port_created']:
            assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

        # get the ids
        result_data = result.data['composite_opticalMultiplexSection']
        oms23_id = result_data['created']['opticalMultiplexSection']['id']
        aport_id = result_data['dependencies_port_created'][0]['port']['id']
        bport_id = result_data['dependencies_port_created'][1]['port']['id']

        # check the integrity of the data
        created_data = result_data['created']['opticalMultiplexSection']

        # check main optical multiplex section
        self.assertEqual(created_data['name'], oms23_name)
        self.assertEqual(created_data['description'], oms23_description)
        self.assertEqual(created_data['operational_state']['value'], oms23_opstate)

        # check their relations id
        test_aport_id = created_data['dependencies'][0]['id']
        test_bport_id = created_data['dependencies'][1]['id']

        self.assertEqual(aport_id, test_aport_id)
        self.assertEqual(bport_id, test_bport_id)

        # check ports in both payload and metatype attribute
        check_aports = [
            created_data['dependencies'][0],
            result_data['dependencies_port_created'][0]['port'],
        ]

        for check_aport in check_aports:
            self.assertEqual(check_aport['name'], aport_name)
            self.assertEqual(check_aport['port_type']['value'], aport_type)
            self.assertEqual(check_aport['description'], aport_description)

        check_bports = [
            created_data['dependencies'][1],
            result_data['dependencies_port_created'][1]['port'],
        ]

        for check_bport in check_bports:
            self.assertEqual(check_bport['name'], bport_name)
            self.assertEqual(check_bport['port_type']['value'], bport_type)
            self.assertEqual(check_bport['description'], bport_description)

        # check provider
        check_provider = result_data['created']['opticalMultiplexSection']['provider']
        self.assertEqual(check_provider['id'], provider_id)
        self.assertEqual(check_provider['name'], provider.node_name)

        ## Update query
        # (do it two times to check that the relationship id is not overwritten)
        relation_id = None
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        for i in range(2):
            buffer_description = oms23_description
            buffer_description2 = aport_description

            oms23_name = "New Optical Multiplex Section"
            oms23_description = bport_descriptionoms233_opstate = random.choice(
                Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

            aport_name = "port-01"
            aport_type = random.choice(
                Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
            aport_description = buffer_description2

            bport_name = "port-02"
            bport_type = random.choice(
                Dropdown.objects.get(name="port_types").as_choices()[1:])[1]
            bport_description = buffer_description

            query = '''
            mutation{{
              composite_opticalMultiplexSection(input:{{
                update_input:{{
                  id: "{oms23_id}"
                  name: "{oms23_name}"
                  description: "{oms23_description}"
                  operational_state: "{oms23_opstate}"
                  relationship_provider: "{provider_id}"
                }}
                update_dependencies_port:[
                  {{
                    id: "{aport_id}"
                    name: "{aport_name}"
                    port_type: "{aport_type}"
                    description: "{aport_description}"
                  }},
                  {{
                    id: "{bport_id}"
                    name: "{bport_name}"
                    port_type: "{bport_type}"
                    description: "{bport_description}"
                  }}
                ]
              }}){{
                updated{{
                  errors{{
                    field
                    messages
                  }}
                  opticalMultiplexSection{{
                    id
                    name
                    description
                    operational_state{{
                      value
                    }}
                    dependencies{{
                      id
                      name
                      ...on Port{{
                        port_type{{
                          value
                        }}
                        description
                      }}
                    }}
                    provider{{
                      id
                      name
                      relation_id
                    }}
                  }}
                }}
                dependencies_port_updated{{
                  errors{{
                    field
                    messages
                  }}
                  port{{
                    id
                    name
                    port_type{{
                      value
                    }}
                    description
                  }}
                }}
              }}
            }}
            '''.format(oms23_name=oms23_name, oms23_description=oms23_description,
                        oms23_opstate=oms23_opstate, aport_name=aport_name,
                        aport_type=aport_type, aport_description=aport_description,
                        bport_name=bport_name, bport_type=bport_type,
                        bport_description=bport_description, oms23_id=oms23_id,
                        aport_id=aport_id, bport_id=bport_id, provider_id=provider_id)

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            # check for errors
            created_errors = result.data['composite_opticalMultiplexSection']\
                                            ['updated']['errors']
            assert not created_errors, pformat(created_errors, indent=1)

            for subcreated in result.data['composite_opticalMultiplexSection']\
                                            ['dependencies_port_updated']:
                assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

            # check the integrity of the data
            result_data = result.data['composite_opticalMultiplexSection']
            updated_data = result_data['updated']['opticalMultiplexSection']

            # check main optical multiplex section
            self.assertEqual(updated_data['name'], oms23_name)
            self.assertEqual(updated_data['description'], oms23_description)
            self.assertEqual(updated_data['operational_state']['value'], oms23_opstate)

            # check their relations id
            test_aport_id = updated_data['dependencies'][0]['id']
            test_bport_id = updated_data['dependencies'][1]['id']

            self.assertEqual(aport_id, test_aport_id)
            self.assertEqual(bport_id, test_bport_id)

            # check ports in both payload and metatype attribute
            check_aports = [
                updated_data['dependencies'][0],
                result_data['dependencies_port_updated'][0]['port'],
            ]

            for check_aport in check_aports:
                self.assertEqual(check_aport['name'], aport_name)
                self.assertEqual(check_aport['port_type']['value'], aport_type)
                self.assertEqual(check_aport['description'], aport_description)

            check_bports = [
                updated_data['dependencies'][1],
                result_data['dependencies_port_updated'][1]['port'],
            ]

            for check_bport in check_bports:
                self.assertEqual(check_bport['name'], bport_name)
                self.assertEqual(check_bport['port_type']['value'], bport_type)
                self.assertEqual(check_bport['description'], bport_description)

            # check provider
            check_provider = result_data['updated']['opticalMultiplexSection']['provider']
            self.assertEqual(check_provider['id'], provider_id)
            self.assertEqual(check_provider['name'], provider.node_name)

            # check that we only have one provider
            _type, oms23_handle_id = relay.Node.from_global_id(oms23_id)
            oms23_nh = NodeHandle.objects.get(handle_id=oms23_handle_id)
            oms23_node = oms23_nh.get_node()
            previous_rels = oms23_node.incoming.get('Provides', [])
            self.assertTrue(len(previous_rels) == 1)

            # check relation_id
            if not relation_id: # first run
                relation_id = check_provider['relation_id']
                self.assertIsNotNone(relation_id)
            else:
                self.assertEqual(relation_id, check_provider['relation_id'])

        ## Update query 2 (remove provider)
        query = '''
        mutation{{
          composite_opticalMultiplexSection(input:{{
            update_input:{{
              id: "{oms23_id}"
              name: "{oms23_name}"
              description: "{oms23_description}"
              operational_state: "{oms23_opstate}"
            }}
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              opticalMultiplexSection{{
                id
                name
                description
                operational_state{{
                  value
                }}
                provider{{
                  id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(oms23_id=oms23_id, oms23_name=oms23_name,
                    oms23_description=oms23_description,
                    oms23_opstate=oms23_opstate)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_opticalMultiplexSection']\
            ['updated']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        # check empty provider
        check_provider = result.data['composite_opticalMultiplexSection']\
            ['updated']['opticalMultiplexSection']['provider']
        self.assertEqual(check_provider, None)


class OpticalPathTest(Neo4jGraphQLNetworkTest):
    def test_optical_path(self):
        opath_name = "Optical Path Test"
        opath_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        opath_wavelength = random.randint(10, 30)

        opath_framing = random.choice(
            Dropdown.objects.get(name="optical_path_framing").as_choices()[1:])[1]

        opath_capacity = random.choice(
            Dropdown.objects.get(name="optical_path_capacity").as_choices()[1:])[1]

        opath_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        odf_name = "ODF test"
        odf_description = "Integer posuere est at sapien elementum, "\
            "ut lacinia mi mattis. Etiam eget aliquet felis. Class aptent "\
            "taciti sociosqu ad litora torquent per conubia nostra, per "\
            "inceptos himenaeos. Sed volutpat feugiat vehicula. Morbi accumsan "\
            "feugiat varius. Morbi id tempus mauris. Morbi ut dapibus odio, "\
            "eget sollicitudin dui."
        odf_rack_units = random.randint(1, 3)
        odf_rack_position = random.randint(1, 5)
        odf_rack_back = bool(random.getrandbits(1))
        odf_opstate = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

        odf_input_str = '''
        create_dependencies_odf:{{
          name: "{odf_name}"
          description: "{odf_description}"
          operational_state: "{odf_opstate}"
          rack_units: {odf_rack_units}
          rack_position: {odf_rack_position}
          rack_back: {odf_rack_back}
        }}
        '''.format(odf_name=odf_name, odf_description=odf_description,
                    odf_opstate=odf_opstate, odf_rack_units=odf_rack_units,
                    odf_rack_position=odf_rack_position,
                    odf_rack_back=str(odf_rack_back).lower())

        odf_query_str = '''
        dependencies_odf_created{
          errors{
            field
            messages
          }
          oDF{
            id
            name
            description
            operational_state{
              id
              value
            }
            rack_units
            rack_position
            rack_back
          }
        }
        '''

        # generate a router
        generator = NetworkFakeDataGenerator()
        router = generator.create_router()
        router_id = relay.Node.to_global_id(str(router.node_type),
                                            str(router.handle_id))

        # get new data to feed the update mutation
        router_rack_units = random.randint(1,10)
        router_rack_position = random.randint(1,10)
        router_rack_back = bool(random.getrandbits(1))

        router_operational_state = random.choice(
            Dropdown.objects.get(name="operational_states").as_choices()[1:][1]
        )
        router_description = generator.escape_quotes(generator.fake.paragraph())

        router_input_str = '''
        update_dependencies_router:{{
          id: "{router_id}"
          description: "{router_description}"
          operational_state: "{router_operational_state}"
          rack_units: {router_rack_units}
          rack_position: {router_rack_position}
          rack_back: {router_rack_back}
        }}
        '''.format(router_id=router_id, router_description=router_description,
                    router_operational_state=router_operational_state,
                    router_rack_units=router_rack_units,
                    router_rack_position=router_rack_position,
                    router_rack_back=str(router_rack_back).lower())

        router_query_str = '''
        dependencies_router_updated{
          errors{
            field
            messages
          }
          router{
            id
            name
            description
            operational_state{
              name
              value
            }
            model
            version
            rack_units
            rack_position
            rack_back
          }
        }
        '''

        # set a provider
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # Create query
        query = '''
        mutation{{
          composite_opticalPath(input:{{
            create_input:{{
              name: "{opath_name}"
              description: "{opath_description}"
              framing: "{opath_framing}"
              capacity: "{opath_capacity}"
              wavelength: {opath_wavelength}
              operational_state: "{opath_opstate}"
              relationship_provider: "{provider_id}"
            }}
            {odf_input_str}
            {router_input_str}
          }}){{
            created{{
              errors{{
                field
                messages
              }}
              opticalPath{{
                id
                name
                description
                framing{{
                  value
                }}
                capacity{{
                  value
                }}
                wavelength
                operational_state{{
                  value
                }}
                dependencies{{
                  id
                  name
                  ...on Port{{
                    port_type{{
                      value
                    }}
                    description
                  }}
                }}
                provider{{
                  id
                  name
                }}
              }}
            }}
            {odf_query_str}
            {router_query_str}
          }}
        }}
        '''.format(opath_name=opath_name, opath_description=opath_description,
                    opath_framing=opath_framing,
                    opath_capacity=opath_capacity,
                    opath_opstate=opath_opstate,
                    provider_id=provider_id, opath_wavelength=opath_wavelength,
                    odf_input_str=odf_input_str, router_input_str=router_input_str,
                    odf_query_str=odf_query_str, router_query_str=router_query_str)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_opticalPath']['created']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        for subcreated in result.data['composite_opticalPath']\
                                    ['dependencies_odf_created']:
            assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

        for subcreated in result.data['composite_opticalPath']\
                                    ['dependencies_router_updated']:
            assert not subcreated['errors'], pformat(subcreated['errors'], indent=1)

        # get the ids
        result_data = result.data['composite_opticalPath']
        opath_id = result_data['created']['opticalPath']['id']
        odf_id = result_data['dependencies_odf_created'][0]['oDF']['id']

        # check the integrity of the data
        created_data = result_data['created']['opticalPath']

        # check main optical path
        self.assertEqual(created_data['name'], opath_name)
        self.assertEqual(created_data['description'], opath_description)
        self.assertEqual(created_data['framing']['value'], opath_framing)
        self.assertEqual(created_data['capacity']['value'], opath_capacity)
        self.assertEqual(created_data['operational_state']['value'], opath_opstate)
        self.assertEqual(created_data['wavelength'], opath_wavelength)

        # check their relations id
        test_odf_id = created_data['dependencies'][1]['id']
        test_router_id = created_data['dependencies'][0]['id']

        self.assertEqual(odf_id, test_odf_id)
        self.assertEqual(router_id, test_router_id)

        # check ports in both payload and metatype attribute
        check_odf = result_data['dependencies_odf_created'][0]['oDF']

        self.assertEqual(check_odf['name'], odf_name)
        self.assertEqual(check_odf['description'], odf_description)
        self.assertEqual(check_odf['operational_state']['value'],
                            odf_opstate)
        self.assertEqual(check_odf['rack_units'], odf_rack_units)
        self.assertEqual(check_odf['rack_position'], odf_rack_position)
        self.assertEqual(check_odf['rack_back'], odf_rack_back)

        check_router = result_data['dependencies_router_updated'][0]['router']

        self.assertEqual(check_router['description'], router_description)
        self.assertEqual(check_router['operational_state']['value'],\
            router_operational_state)
        self.assertEqual(check_router ['rack_units'], router_rack_units)
        self.assertEqual(check_router['rack_position'], router_rack_position)
        self.assertEqual(check_router['rack_back'], router_rack_back)

        # check provider
        check_provider = result_data['created']['opticalPath']['provider']
        self.assertEqual(check_provider['id'], provider_id)
        self.assertEqual(check_provider['name'], provider.node_name)

        ## Update query
        # (do it two times to check that the relationship id is not overwritten)
        relation_id = None
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        for i in range(2):
            opath_name = "New Optical Path"
            opath_description = router_description
            opath_wavelength = random.randint(10, 30)

            opath_framing = random.choice(
                Dropdown.objects.get(name="optical_path_framing").as_choices()[1:])[1]

            opath_capacity = random.choice(
                Dropdown.objects.get(name="optical_path_capacity").as_choices()[1:])[1]

            opath_opstate = random.choice(
                Dropdown.objects.get(name="operational_states").as_choices()[1:])[1]

            query = '''
            mutation{{
              composite_opticalPath(input:{{
                update_input:{{
                  id: "{opath_id}"
                  name: "{opath_name}"
                  description: "{opath_description}"
                  framing: "{opath_framing}"
                  capacity: "{opath_capacity}"
                  wavelength: {opath_wavelength}
                  operational_state: "{opath_opstate}"
                  relationship_provider: "{provider_id}"
                }}
              }}){{
                updated{{
                  errors{{
                    field
                    messages
                  }}
                  opticalPath{{
                    id
                    name
                    description
                    framing{{
                      value
                    }}
                    capacity{{
                      value
                    }}
                    wavelength
                    operational_state{{
                      value
                    }}
                    dependencies{{
                      id
                      name
                      ...on Port{{
                        port_type{{
                          value
                        }}
                        description
                      }}
                    }}
                    provider{{
                      id
                      name
                      relation_id
                    }}
                  }}
                }}
              }}
            }}
            '''.format(opath_name=opath_name,
                        opath_description=opath_description,
                        opath_framing=opath_framing,
                        opath_capacity=opath_capacity,
                        opath_opstate=opath_opstate,
                        provider_id=provider_id,
                        opath_wavelength=opath_wavelength,
                        opath_id=opath_id)

            result = schema.execute(query, context=self.context)
            assert not result.errors, pformat(result.errors, indent=1)

            # check for errors
            created_errors = result.data['composite_opticalPath']['updated']['errors']
            assert not created_errors, pformat(created_errors, indent=1)

            # check the integrity of the data
            result_data = result.data['composite_opticalPath']
            updated_data = result_data['updated']['opticalPath']

            # check main optical path
            self.assertEqual(updated_data['name'], opath_name)
            self.assertEqual(updated_data['description'], opath_description)
            self.assertEqual(updated_data['framing']['value'], opath_framing)
            self.assertEqual(updated_data['capacity']['value'], opath_capacity)
            self.assertEqual(updated_data['operational_state']['value'], opath_opstate)
            self.assertEqual(updated_data['wavelength'], opath_wavelength)

            # check provider
            check_provider = result_data['updated']['opticalPath']['provider']
            self.assertEqual(check_provider['id'], provider_id)
            self.assertEqual(check_provider['name'], provider.node_name)

            # check that we only have one provider
            _type, opath_handle_id = relay.Node.from_global_id(opath_id)
            opath_nh = NodeHandle.objects.get(handle_id=opath_handle_id)
            opath_node = opath_nh.get_node()
            previous_rels = opath_node.incoming.get('Provides', [])
            self.assertTrue(len(previous_rels) == 1)

            # check relation_id
            if not relation_id: # first run
                relation_id = check_provider['relation_id']
                self.assertIsNotNone(relation_id)
            else:
                self.assertEqual(relation_id, check_provider['relation_id'])

        ## Update query 2 (remove provider)
        query = '''
        mutation{{
          composite_opticalPath(input:{{
            update_input:{{
              id: "{opath_id}"
              name: "{opath_name}"
              description: "{opath_description}"
              framing: "{opath_framing}"
              capacity: "{opath_capacity}"
              wavelength: {opath_wavelength}
              operational_state: "{opath_opstate}"
            }}
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              opticalPath{{
                id
                name
                description
                framing{{
                  value
                }}
                capacity{{
                  value
                }}
                wavelength
                operational_state{{
                  value
                }}
                provider{{
                  id
                  name
                }}
              }}
            }}
          }}
        }}
        '''.format(opath_id=opath_id, opath_name=opath_name,
                    opath_description=opath_description,
                    opath_framing=opath_framing,
                    opath_capacity=opath_capacity,
                    opath_opstate=opath_opstate,
                    opath_wavelength=opath_wavelength)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        created_errors = result.data['composite_opticalPath']['updated']['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        # check empty provider
        check_provider = result.data['composite_opticalPath']['updated']['opticalPath']['provider']
        self.assertEqual(check_provider, None)


## Peering
class PeeringGroupTest(Neo4jGraphQLNetworkTest):
    def test_peering_group(self):
        data_generator = NetworkFakeDataGenerator()
        pgroup = data_generator.create_peering_group()

        pg_type_str = pgroup.node_type.type.replace(' ', '')
        peergroup_id = relay.Node.to_global_id(pg_type_str,
                                        str(pgroup.handle_id))
        peergroup_name = "Peer Group new name"

        # modify dependencies
        dependencies = pgroup.get_node().get_dependencies()
        unit1_handle_id = dependencies['Depends_on'][0]['relationship']\
                            .end_node._properties['handle_id']
        unit1_nh = NodeHandle.objects.get(handle_id=unit1_handle_id)
        unit1_id = relay.Node.to_global_id(str(unit1_nh.node_type),
                                        str(unit1_nh.handle_id))
        unit1_name = "Test dependency unit"
        unit1_description = unit1_nh.get_node().data.get("description")
        unit1_vlan = unit1_nh.get_node().data.get("vlan")

        unit2_handle_id = dependencies['Depends_on'][1]['relationship']\
                            .end_node._properties['handle_id']
        unit2_nh = NodeHandle.objects.get(handle_id=unit2_handle_id)
        unit2_id = relay.Node.to_global_id(str(unit2_nh.node_type),
                                        str(unit2_nh.handle_id))

        # add new peering partner user
        peering_partner = data_generator.create_peering_partner()
        ppartner_id = relay.Node.to_global_id(
                            str(peering_partner.node_type.type.replace(' ', '')),
                            str(peering_partner.handle_id))
        ppartner_name = "Test Peering Partner"

        query = """
        mutation{{
          composite_peeringGroup(input:{{
            update_input:{{
              id: "{peergroup_id}"
              name: "{peergroup_name}"
            }}
            update_dependencies_unit:{{
              id: "{unit1_id}"
              name: "{unit1_name}"
              description: "{unit1_description}"
              vlan: "{unit1_vlan}"
            }}
            deleted_dependencies_unit:{{
              id: "{unit2_id}"
            }}
            update_used_by_peeringpartner:{{
              id: "{ppartner_id}"
              name: "{ppartner_name}"
            }}
          }}){{
            updated{{
              errors{{
                field
                messages
              }}
              peeringGroup{{
                id
                name
                dependencies{{
                  __typename
                  id
                  name
                  relation_id
                  ...on Logical{{
                    dependencies{{
                      __typename
                      id
                      name
                    }}
                    part_of{{
                      __typename
                      id
                      name
                    }}
                  }}
                  ...on Unit{{
                    description
                    vlan
                    ip_address
                  }}
                }}
                used_by{{
                  __typename
                  id
                  name
                  relation_id
                  ...on PeeringPartner{{
                    ip_address
                    as_number
                    peering_link
                  }}
                }}
              }}
            }}
            dependencies_unit_updated{{
              errors{{
                field
                messages
              }}
              unit{{
                id
                name
                description
                vlan
              }}
            }}
            dependencies_unit_deleted{{
              success
            }}
            used_by_peeringpartner_updated{{
              errors{{
                field
                messages
              }}
              peeringPartner{{
                id
                name
              }}
            }}
          }}
        }}
        """.format(peergroup_id=peergroup_id, peergroup_name=peergroup_name,
                    unit1_id=unit1_id, unit1_name=unit1_name,
                    unit1_description=unit1_description, unit1_vlan=unit1_vlan,
                    unit2_id=unit2_id, ppartner_id=ppartner_id,
                    ppartner_name=ppartner_name)

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        updated_errors = \
            result.data['composite_peeringGroup']['updated']['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_peeringGroup']['dependencies_unit_updated']\
                        [0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        subupdated_errors = \
            result.data['composite_peeringGroup']\
                        ['used_by_peeringpartner_updated'][0]['errors']
        assert not subupdated_errors, pformat(subupdated_errors, indent=1)

        # check data
        updated_pgroup = result.data['composite_peeringGroup']['updated']\
                            ['peeringGroup']
        self.assertEqualIds(updated_pgroup['id'], peergroup_id)
        self.assertEquals(updated_pgroup['name'], peergroup_name)

        # check subentities
        check_unit1 = result.data \
            ['composite_peeringGroup']['dependencies_unit_updated'][0]['unit']

        self.assertEquals(check_unit1['name'], unit1_name)
        self.assertEquals(check_unit1['description'], unit1_description)
        self.assertEquals(check_unit1['vlan'], unit1_vlan)

        is_present = False
        for dep in updated_pgroup['dependencies']:
            if dep['id'] == unit1_id:
                is_present = True

        self.assertTrue(is_present)

        check_unit2_deletion = result.data \
            ['composite_peeringGroup']['dependencies_unit_deleted'][0]['success']
        self.assertTrue(check_unit2_deletion)

        check_ppartner = result.data \
            ['composite_peeringGroup']['used_by_peeringpartner_updated']\
            [0]['peeringPartner']

        self.assertEquals(check_ppartner['name'], ppartner_name)

        is_present = False
        for dep in updated_pgroup['used_by']:
            if dep['id'] == ppartner_id:
                is_present = True

        self.assertTrue(is_present)


class SiteTest(Neo4jGraphQLNetworkTest):
    def test_site(self):
        data_generator = NetworkFakeDataGenerator()

        ## creation

        # create responsible for
        site_owner = data_generator.create_site_owner()
        responsible_for_id = relay.Node.to_global_id(str(site_owner.node_type),
                                            str(site_owner.handle_id))

        # create a parent site
        parent_site = data_generator.create_site()
        parent_site_id = relay.Node.to_global_id(str(parent_site.node_type),
                                            str(parent_site.handle_id))
        parent_site_name = "Parent Site"
        parent_site_country = parent_site.get_node().data.get("country")
        parent_site_type = parent_site.get_node().data.get("site_type")
        parent_site_type = '' if not parent_site_type else parent_site_type
        parent_site_area = parent_site.get_node().data.get("area")
        parent_site_longitude = parent_site.get_node().data.get("longitude")
        parent_site_latitude = parent_site.get_node().data.get("latitude")
        parent_site_owner_id = parent_site.get_node().data.get("owner_id")
        parent_site_owner_site_name = parent_site.get_node().data.get("owner_site_name")
        parent_site_url = parent_site.get_node().data.get("url")
        parent_site_telenor_subscription_id = parent_site.get_node().data.get("telenor_subscription_id")

        # has data room
        has_room = data_generator.create_room(add_parent=False)
        has_room_name = has_room.get_node().data.get("name")
        has_room_floor = has_room.get_node().data.get("floor")
        has_room.delete()

        # create firewall
        firewall = data_generator.create_firewall()
        firewall_id = relay.Node.to_global_id(str(firewall.node_type),
                                            str(firewall.handle_id))
        firewall_name = "Test firewall"
        firewall_opstate = firewall.get_node().data.get("operational_state")

        # create switch
        switch = data_generator.create_switch()
        switch_id = relay.Node.to_global_id(str(switch.node_type),
                                            str(switch.handle_id))
        switch_name = "Test switch"
        switch_opstate = switch.get_node().data.get("operational_state")

        # generate test data, we'll remove these later
        # create a site to use its data
        a_site = data_generator.create_site()
        site_name = "Test Site"
        site_country = a_site.get_node().data.get("country")
        site_type = a_site.get_node().data.get("site_type")
        site_type = '' if not site_type else site_type
        site_area = a_site.get_node().data.get("area")
        site_longitude = a_site.get_node().data.get("longitude")
        site_latitude = a_site.get_node().data.get("latitude")
        site_owner_id = a_site.get_node().data.get("owner_id")
        site_owner_site_name = a_site.get_node().data.get("owner_site_name")
        site_url = a_site.get_node().data.get("url")
        site_telenor_subscription_id = a_site.get_node().data.get("telenor_subscription_id")

        # create two address
        address1 = data_generator.create_address()
        address2 = data_generator.create_address()

        address1_name = address1.get_node().data.get("name")
        address1_phone = address1.get_node().data.get("phone")
        address1_street = address1.get_node().data.get("street")\
                            .replace('\n', ' ')
        address1_floor = address1.get_node().data.get("floor")\
                            .replace('\n', ' ')
        address1_room = address1.get_node().data.get("room")
        address1_postal_code = address1.get_node().data.get("postal_code")
        address1_postal_area = address1.get_node().data.get("postal_area")

        address2_name = address2.get_node().data.get("name")
        address2_phone = address2.get_node().data.get("phone")
        address2_street = address2.get_node().data.get("street")\
                            .replace('\n', ' ')
        address2_floor = address2.get_node().data.get("floor")\
                            .replace('\n', ' ')
        address2_room = address2.get_node().data.get("room")
        address2_postal_code = address2.get_node().data.get("postal_code")
        address2_postal_area = address2.get_node().data.get("postal_area")

        main_input = "create_input"
        main_input_id = ""
        subinputs_input = "create_subinputs"
        subinput1_id = ""
        subinput2_id = ""
        has_input = "create_has_room"
        has_input_id = ""
        main_payload = "created"
        subpayload = "subcreated"
        has_payload = "has_room_created"

        query_t = """
        mutation{{
          composite_site(input:{{
            {main_input}:{{
              {main_input_id}
              name: "{site_name}"
              country: "{site_country}"
              site_type: "{site_type}"
              area: "{site_area}"
              longitude: {site_longitude}
              latitude: {site_latitude}
              owner_id: "{site_owner_id}"
              owner_site_name: "{site_owner_site_name}"
              url: "{site_url}"
              telenor_subscription_id: "{site_telenor_subscription_id}"
              relationship_responsible_for: "{responsible_for_id}"
            }}
            {subinputs_input}:[
              {{
                {subinput1_id}
                name: "{address1_name}"
                phone: "{address1_phone}"
                street: "{address1_street}"
                floor: "{address1_floor}"
                room: "{address1_room}"
                postal_code: "{address1_postal_code}"
                postal_area: "{address1_postal_area}"
              }}
              {{
                {subinput2_id}
                name: "{address2_name}"
                phone: "{address2_phone}"
                street: "{address2_street}"
                floor: "{address2_floor}"
                room: "{address2_room}"
                postal_code: "{address2_postal_code}"
                postal_area: "{address2_postal_area}"
              }}
            ]
            update_parent_site: {{
              id: "{parent_site_id}"
              name: "{parent_site_name}"
              country: "{parent_site_country}"
              site_type: "{parent_site_type}"
              area: "{parent_site_area}"
              longitude: {parent_site_longitude}
              latitude: {parent_site_latitude}
              owner_id: "{parent_site_owner_id}"
              owner_site_name: "{parent_site_owner_site_name}"
              url: "{parent_site_url}"
              telenor_subscription_id: "{parent_site_telenor_subscription_id}"
              relationship_responsible_for: "{responsible_for_id}"
            }}
            update_located_in_firewall:[
              {{
                id: "{firewall_id}"
                name: "{firewall_name}"
                operational_state: "{firewall_opstate}"
              }}
            ]
            update_located_in_switch:[
              {{
                id: "{switch_id}"
                name: "{switch_name}"
                operational_state: "{switch_opstate}"
              }}
            ]
            {has_input}:[ # TODO add has_room instead
              {{
                {has_input_id}
                name: "{has_room_name}"
                floor: "{has_room_floor}"
              }}
            ]
          }}){{
            {main_payload}{{
              errors{{
                field
                messages
              }}
              site{{
                id
                name
                country_code{{
                  name
                  value
                }}
                country
                site_type{{
                  name
                  value
                }}
                area
                latitude
                longitude
                owner_id
                owner_site_name
                url
                telenor_subscription_id
                responsible_for{{
                  __typename
                  id
                  name
                }}
                addresses{{
                  id
                  name
                  phone
                  street
                  floor
                  room
                  postal_code
                  postal_area
                }}
                parent{{
                  __typename
                  ...on Site{{
                    id
                    name
                    country_code{{
                      name
                      value
                    }}
                    country
                    site_type{{
                      name
                      value
                    }}
                    area
                    latitude
                    longitude
                    owner_id
                    owner_site_name
                    url
                    telenor_subscription_id
                    responsible_for{{
                      __typename
                      id
                      name
                    }}
                  }}
                }}
                located_in{{
                  __typename
                  id
                  name
                  ...on Firewall{{
                    operational_state{{
                      value
                    }}
                    ip_addresses
                  }}
                  ...on Switch{{
                    operational_state{{
                      value
                    }}
                    ip_addresses
                  }}
                }}
                has{{
                  __typename
                  id
                  name
                  ...on Site{{
                    country_code{{
                      name
                      value
                    }}
                    country
                    site_type{{
                      name
                      value
                    }}
                    area
                    latitude
                    longitude
                    owner_id
                    owner_site_name
                    url
                    telenor_subscription_id
                  }}
                }}
              }}
            }}
            {subpayload}{{
              errors{{
                field
                messages
              }}
              address{{
                id
                name
                phone
                street
                floor
                room
                postal_code
                postal_area
              }}
            }}
            parent_site_updated{{
              errors{{
                field
                messages
              }}
              site{{
                id
                name
                country_code{{
                  name
                  value
                }}
                country
                site_type{{
                  name
                  value
                }}
                area
                latitude
                longitude
                owner_id
                owner_site_name
                url
                telenor_subscription_id
              }}
            }}
            located_in_firewall_updated{{
              errors{{
                field
                messages
              }}
              firewall{{
                id
                name
                operational_state{{
                  value
                }}
              }}
            }}
            located_in_switch_updated{{
              errors{{
                field
                messages
              }}
              switch{{
                id
                name
                operational_state{{
                  value
                }}
              }}
            }}
            {has_payload}{{
              errors{{
                field
                messages
              }}
              room{{
                id
                name
                floor
              }}
            }}
          }}
        }}
        """

        query = query_t.format(
            main_input=main_input, main_input_id=main_input_id,
            subinputs_input=subinputs_input, subinput1_id=subinput1_id,
            subinput2_id=subinput2_id,
            has_input=has_input, has_input_id=has_input_id,
            main_payload=main_payload, subpayload=subpayload,
            has_payload=has_payload,
            site_name=site_name, site_country=site_country,
            site_type=site_type, site_area=site_area,
            site_longitude=site_longitude, site_latitude=site_latitude,
            site_owner_id=site_owner_id,
            site_owner_site_name=site_owner_site_name,
            site_url=site_url,
            site_telenor_subscription_id=site_telenor_subscription_id,
            responsible_for_id=responsible_for_id,
            address1_name=address1_name, address1_phone=address1_phone,
            address1_street=address1_street, address1_floor=address1_floor,
            address1_room=address1_room,
            address1_postal_code=address1_postal_code,
            address1_postal_area=address1_postal_area,
            address2_name=address2_name, address2_phone=address2_phone,
            address2_street=address2_street, address2_floor=address2_floor,
            address2_room=address2_room,
            address2_postal_code=address2_postal_code,
            address2_postal_area=address2_postal_area,
            parent_site_id=parent_site_id,
            parent_site_name=parent_site_name, parent_site_country=parent_site_country,
            parent_site_type=parent_site_type, parent_site_area=parent_site_area,
            parent_site_longitude=parent_site_longitude, parent_site_latitude=parent_site_latitude,
            parent_site_owner_id=parent_site_owner_id,
            parent_site_owner_site_name=parent_site_owner_site_name,
            parent_site_url=parent_site_url,
            parent_site_telenor_subscription_id=parent_site_telenor_subscription_id,
            has_room_name=has_room_name, has_room_floor=has_room_floor,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
        )

        # delete generated nodes
        a_site.delete()
        address1.delete()
        address2.delete()

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_site']
        created_errors = all_data[main_payload]['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        submutations = {
            subpayload: None,
            'parent_site_updated': None,
            'located_in_firewall_updated': None,
            'located_in_switch_updated': None,
            has_payload: None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], \
                            pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], \
                        pformat(submutations[k], indent=1)


        # check site data
        check_site = all_data[main_payload]['site']
        site_id = check_site['id']

        self.assertEquals(check_site['name'], site_name)
        self.assertEquals(check_site['country_code']['name'], site_country)
        if site_type:
            self.assertEquals(check_site['site_type']['value'], site_type)
        self.assertEquals(check_site['area'], site_area)
        self.assertEquals(check_site['latitude'], site_latitude)
        self.assertEquals(check_site['longitude'], site_longitude)
        self.assertEquals(check_site['owner_id'], site_owner_id)
        self.assertEquals(check_site['owner_site_name'], site_owner_site_name)
        self.assertEquals(check_site['url'], site_url)
        self.assertEquals(check_site['telenor_subscription_id'], \
            site_telenor_subscription_id)

        # check address
        check_address1 = all_data[subpayload][0]['address']
        address1_id = check_address1['id']

        self.assertEquals(check_address1['name'], address1_name)
        self.assertEquals(check_address1['phone'], address1_phone)
        self.assertEquals(check_address1['street'], address1_street)
        self.assertEquals(check_address1['floor'], address1_floor)
        self.assertEquals(check_address1['room'], address1_room)
        self.assertEquals(check_address1['postal_code'], address1_postal_code)
        self.assertEquals(check_address1['postal_area'], address1_postal_area)

        self.assertEquals(check_site['addresses'][0]['id'], address1_id)

        check_address2 = all_data[subpayload][1]['address']
        address2_id = check_address2['id']

        self.assertEquals(check_address2['name'], address2_name)
        self.assertEquals(check_address2['phone'], address2_phone)
        self.assertEquals(check_address2['street'], address2_street)
        self.assertEquals(check_address2['floor'], address2_floor)
        self.assertEquals(check_address2['room'], address2_room)
        self.assertEquals(check_address2['postal_code'], address2_postal_code)
        self.assertEquals(check_address2['postal_area'], address2_postal_area)

        self.assertEquals(check_site['addresses'][1]['id'], address2_id)

        # check parent site data
        check_parent_site = all_data\
                                ['parent_site_updated']['site']

        self.assertEquals(check_parent_site['id'], parent_site_id)
        self.assertEquals(check_parent_site['name'], parent_site_name)
        self.assertEquals(check_parent_site['country_code']['name'], parent_site_country)
        if parent_site_type:
            self.assertEquals(check_parent_site['site_type']['value'], parent_site_type)
        self.assertEquals(check_parent_site['area'], parent_site_area)
        self.assertEquals(check_parent_site['latitude'], parent_site_latitude)
        self.assertEquals(check_parent_site['longitude'], parent_site_longitude)
        self.assertEquals(check_parent_site['owner_id'], parent_site_owner_id)
        self.assertEquals(check_parent_site['owner_site_name'], parent_site_owner_site_name)
        self.assertEquals(check_parent_site['url'], parent_site_url)
        self.assertEquals(check_parent_site['telenor_subscription_id'], \
            parent_site_telenor_subscription_id)


        # check firewall
        check_firewall = all_data\
                            ['located_in_firewall_updated'][0]['firewall']

        self.assertEquals(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEquals(check_site['located_in'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data\
                            ['located_in_switch_updated'][0]['switch']

        self.assertEquals(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEquals(check_site['located_in'][1]['id'], switch_id)

        # check has room
        check_has_room = all_data[has_payload][0]['room']
        has_room_id = check_has_room['id']

        self.assertEquals(check_has_room['name'], has_room_name)
        self.assertEquals(check_has_room['floor'], has_room_floor)
        self.assertEquals(check_site['has'][0]['id'], has_room_id)

        ## edition
        # create another responsible for
        site_owner = data_generator.create_site_owner()
        responsible_for_id = relay.Node.to_global_id(str(site_owner.node_type),
                                            str(site_owner.handle_id))

        # create another parent site
        parent_site = data_generator.create_site()
        parent_site_id = relay.Node.to_global_id(str(parent_site.node_type),
                                            str(parent_site.handle_id))
        parent_site_name = "Parent Site"
        parent_site_country = parent_site.get_node().data.get("country")
        parent_site_type = parent_site.get_node().data.get("site_type")
        parent_site_type = '' if not parent_site_type else parent_site_type
        parent_site_area = parent_site.get_node().data.get("area")
        parent_site_longitude = parent_site.get_node().data.get("longitude")
        parent_site_latitude = parent_site.get_node().data.get("latitude")
        parent_site_owner_id = parent_site.get_node().data.get("owner_id")
        parent_site_owner_site_name = parent_site.get_node().data.get("owner_site_name")
        parent_site_url = parent_site.get_node().data.get("url")
        parent_site_telenor_subscription_id = parent_site.get_node().data.get("telenor_subscription_id")

        # create room node and delete so we can update the has room data
        has_room = data_generator.create_room(add_parent=False)
        has_room_name = has_room.get_node().data.get("name")
        has_room_floor = has_room.get_node().data.get("floor")
        has_room.delete()

        # create firewall and delete it to get it's generated data
        firewall = data_generator.create_firewall()

        firewall_name = firewall.get_node().data.get("name")
        firewall_opstate = firewall.get_node().data.get("operational_state")
        firewall.delete()

        # create another and delete it to get it's generated data
        switch = data_generator.create_switch()

        switch_name = switch.get_node().data.get("name")
        switch_opstate = switch.get_node().data.get("operational_state")
        switch.delete()

        # generate test data, we'll remove these later
        # create a site to use its data
        a_site = data_generator.create_site()
        site_name = "New test Site"
        site_country = a_site.get_node().data.get("country")
        site_type = a_site.get_node().data.get("site_type")
        site_type = '' if not site_type else site_type
        site_area = a_site.get_node().data.get("area")
        site_longitude = a_site.get_node().data.get("longitude")
        site_latitude = a_site.get_node().data.get("latitude")
        site_owner_id = a_site.get_node().data.get("owner_id")
        site_owner_site_name = a_site.get_node().data.get("owner_site_name")
        site_url = a_site.get_node().data.get("url")
        site_telenor_subscription_id = a_site.get_node().data.get("telenor_subscription_id")

        # create two address and get its data
        address1 = data_generator.create_address()
        address2 = data_generator.create_address()

        address1_name = address1.get_node().data.get("name")
        address1_phone = address1.get_node().data.get("phone")
        address1_street = address1.get_node().data.get("street")\
                            .replace('\n', ' ')
        address1_floor = address1.get_node().data.get("floor")\
                            .replace('\n', ' ')
        address1_room = address1.get_node().data.get("room")
        address1_postal_code = address1.get_node().data.get("postal_code")
        address1_postal_area = address1.get_node().data.get("postal_area")

        address2_name = address2.get_node().data.get("name")
        address2_phone = address2.get_node().data.get("phone")
        address2_street = address2.get_node().data.get("street")\
                            .replace('\n', ' ')
        address2_floor = address2.get_node().data.get("floor")\
                            .replace('\n', ' ')
        address2_room = address2.get_node().data.get("room")
        address2_postal_code = address2.get_node().data.get("postal_code")
        address2_postal_area = address2.get_node().data.get("postal_area")

        a_site.delete()
        address1.delete()
        address2.delete()

        main_input = 'update_input'
        main_input_id = 'id: "{}"'.format(site_id)
        subinputs_input = "update_subinputs"
        subinput1_id = 'id: "{}"'.format(address1_id)
        subinput2_id = 'id: "{}"'.format(address2_id)
        has_input = 'update_has_room'
        has_input_id = 'id: "{}"'.format(has_room_id)
        main_payload = "updated"
        subpayload = "subupdated"
        has_payload = "has_room_updated"

        query = query_t.format(
            main_input=main_input, main_input_id=main_input_id,
            subinputs_input=subinputs_input, subinput1_id=subinput1_id,
            subinput2_id=subinput2_id,
            has_input=has_input, has_input_id=has_input_id,
            main_payload=main_payload, subpayload=subpayload,
            has_payload=has_payload,
            site_name=site_name, site_country=site_country,
            site_type=site_type, site_area=site_area,
            site_longitude=site_longitude, site_latitude=site_latitude,
            site_owner_id=site_owner_id,
            site_owner_site_name=site_owner_site_name,
            site_url=site_url,
            site_telenor_subscription_id=site_telenor_subscription_id,
            responsible_for_id=responsible_for_id,
            address1_name=address1_name, address1_phone=address1_phone,
            address1_street=address1_street, address1_floor=address1_floor,
            address1_room=address1_room,
            address1_postal_code=address1_postal_code,
            address1_postal_area=address1_postal_area,
            address2_name=address2_name, address2_phone=address2_phone,
            address2_street=address2_street, address2_floor=address2_floor,
            address2_room=address2_room,
            address2_postal_code=address2_postal_code,
            address2_postal_area=address2_postal_area,
            parent_site_id=parent_site_id,
            parent_site_name=parent_site_name, parent_site_country=parent_site_country,
            parent_site_type=parent_site_type, parent_site_area=parent_site_area,
            parent_site_longitude=parent_site_longitude, parent_site_latitude=parent_site_latitude,
            parent_site_owner_id=parent_site_owner_id,
            parent_site_owner_site_name=parent_site_owner_site_name,
            parent_site_url=parent_site_url,
            parent_site_telenor_subscription_id=parent_site_telenor_subscription_id,
            has_room_name=has_room_name, has_room_floor=has_room_floor,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_site']
        created_errors = all_data[main_payload]['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        submutations = {
            subpayload: None,
            'parent_site_updated': None,
            'located_in_firewall_updated': None,
            'located_in_switch_updated': None,
            has_payload: None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], pformat(submutations[k], indent=1)

        # check site data
        check_site = all_data[main_payload]['site']
        site_id = check_site['id']

        self.assertEquals(check_site['name'], site_name)
        self.assertEquals(check_site['country_code']['name'], site_country)
        if site_type:
            self.assertEquals(check_site['site_type']['value'], site_type)
        self.assertEquals(check_site['area'], site_area)
        self.assertEquals(check_site['latitude'], site_latitude)
        self.assertEquals(check_site['longitude'], site_longitude)
        self.assertEquals(check_site['owner_id'], site_owner_id)
        self.assertEquals(check_site['owner_site_name'], site_owner_site_name)
        self.assertEquals(check_site['url'], site_url)
        self.assertEquals(check_site['telenor_subscription_id'], \
            site_telenor_subscription_id)

        # check address
        check_address1 = all_data[subpayload][0]['address']
        address1_id = check_address1['id']

        self.assertEquals(check_address1['name'], address1_name)
        self.assertEquals(check_address1['phone'], address1_phone)
        self.assertEquals(check_address1['street'], address1_street)
        self.assertEquals(check_address1['floor'], address1_floor)
        self.assertEquals(check_address1['room'], address1_room)
        self.assertEquals(check_address1['postal_code'], address1_postal_code)
        self.assertEquals(check_address1['postal_area'], address1_postal_area)

        self.assertEquals(check_site['addresses'][0]['id'], address1_id)

        check_address2 = all_data[subpayload][1]['address']
        address2_id = check_address2['id']

        self.assertEquals(check_address2['name'], address2_name)
        self.assertEquals(check_address2['phone'], address2_phone)
        self.assertEquals(check_address2['street'], address2_street)
        self.assertEquals(check_address2['floor'], address2_floor)
        self.assertEquals(check_address2['room'], address2_room)
        self.assertEquals(check_address2['postal_code'], address2_postal_code)
        self.assertEquals(check_address2['postal_area'], address2_postal_area)

        self.assertEquals(check_site['addresses'][1]['id'], address2_id)

        # check parent site data
        check_parent_site = all_data['parent_site_updated']['site']

        self.assertEquals(check_parent_site['id'], parent_site_id)
        self.assertEquals(check_parent_site['name'], parent_site_name)
        self.assertEquals(check_parent_site['country_code']['name'], parent_site_country)
        if parent_site_type:
            self.assertEquals(check_parent_site['site_type']['value'], parent_site_type)
        self.assertEquals(check_parent_site['area'], parent_site_area)
        self.assertEquals(check_parent_site['latitude'], parent_site_latitude)
        self.assertEquals(check_parent_site['longitude'], parent_site_longitude)
        self.assertEquals(check_parent_site['owner_id'], parent_site_owner_id)
        self.assertEquals(check_parent_site['owner_site_name'], parent_site_owner_site_name)
        self.assertEquals(check_parent_site['url'], parent_site_url)
        self.assertEquals(check_parent_site['telenor_subscription_id'], \
            parent_site_telenor_subscription_id)


        # check firewall
        check_firewall = all_data['located_in_firewall_updated'][0]['firewall']

        self.assertEquals(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEquals(check_site['located_in'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data['located_in_switch_updated'][0]['switch']

        self.assertEquals(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEquals(check_site['located_in'][1]['id'], switch_id)

        # check has room
        check_has_room = all_data[has_payload][0]['room']

        self.assertEquals(check_has_room['name'], has_room_name)
        self.assertEquals(check_has_room['floor'], has_room_floor)
        self.assertEquals(check_site['has'][0]['id'], has_room_id)


class RoomTest(Neo4jGraphQLNetworkTest):
    def test_room(self):
        data_generator = NetworkFakeDataGenerator()

        ## creation
        # data room
        a_room = data_generator.create_room(add_parent=False)
        room_name = a_room.get_node().data.get("name")
        room_floor = a_room.get_node().data.get("floor")
        a_room.delete()

        # has data rack
        has_rack = data_generator.create_rack(add_parent=False)
        has_rack_name = has_rack.get_node().data.get("name")
        has_rack_height = has_rack.get_node().data.get("height")
        has_rack_depth = has_rack.get_node().data.get("depth")
        has_rack_width = has_rack.get_node().data.get("width")
        has_rack_rack_units = has_rack.get_node().data.get("rack_units")
        has_rack.delete()

        # create responsible for
        site_owner = data_generator.create_site_owner()
        responsible_for_id = relay.Node.to_global_id(str(site_owner.node_type),
                                            str(site_owner.handle_id))

        # create a parent site
        parent_site = data_generator.create_site()
        parent_site_id = relay.Node.to_global_id(str(parent_site.node_type),
                                            str(parent_site.handle_id))
        parent_site_name = "Parent Site"
        parent_site_country = parent_site.get_node().data.get("country")
        parent_site_type = parent_site.get_node().data.get("site_type")
        parent_site_type = '' if not parent_site_type else parent_site_type
        parent_site_area = parent_site.get_node().data.get("area")
        parent_site_longitude = parent_site.get_node().data.get("longitude")
        parent_site_latitude = parent_site.get_node().data.get("latitude")
        parent_site_owner_id = parent_site.get_node().data.get("owner_id")
        parent_site_owner_site_name = parent_site.get_node().data.get("owner_site_name")
        parent_site_url = parent_site.get_node().data.get("url")
        parent_site_telenor_subscription_id = parent_site.get_node().data.get("telenor_subscription_id")

        # create firewall
        firewall = data_generator.create_firewall()
        firewall_id = relay.Node.to_global_id(str(firewall.node_type),
                                            str(firewall.handle_id))
        firewall_name = "Test firewall"
        firewall_opstate = firewall.get_node().data.get("operational_state")

        # create switch
        switch = data_generator.create_switch()
        switch_id = relay.Node.to_global_id(str(switch.node_type),
                                            str(switch.handle_id))
        switch_name = "Test switch"
        switch_opstate = switch.get_node().data.get("operational_state")

        main_input = "create_input"
        main_input_id = ""
        has_input = "create_has_rack"
        has_input_id = ""
        main_payload = "created"
        has_payload = "has_rack_created"

        query_t = """
        mutation{{
          composite_room(input:{{
            {main_input}: {{
              {main_input_id}
              name: "{room_name}"
              floor: "{room_floor}"
            }}
            update_parent_site: {{
              id: "{parent_site_id}"
              name: "{parent_site_name}"
              country: "{parent_site_country}"
              site_type: "{parent_site_type}"
              area: "{parent_site_area}"
              longitude: {parent_site_longitude}
              latitude: {parent_site_latitude}
              owner_id: "{parent_site_owner_id}"
              owner_site_name: "{parent_site_owner_site_name}"
              url: "{parent_site_url}"
              telenor_subscription_id: "{parent_site_telenor_subscription_id}"
              relationship_responsible_for: "{responsible_for_id}"
            }}
            update_located_in_firewall:[
              {{
                id: "{firewall_id}"
                name: "{firewall_name}"
                operational_state: "{firewall_opstate}"
              }}
            ]
            update_located_in_switch:[
              {{
                id: "{switch_id}"
                name: "{switch_name}"
                operational_state: "{switch_opstate}"
              }}
            ]
            {has_input}:{{
              {has_input_id}
              name: "{has_rack_name}"
              height: {has_rack_height}
              depth: {has_rack_depth}
              width: {has_rack_width}
              rack_units: {has_rack_rack_units}
            }}
          }}){{
            {main_payload}{{
              errors{{
                field
                messages
              }}
              room{{
                id
                name
                floor
                parent{{
                  ...on Site{{
                    id
                    name
                    country_code{{
                      name
                      value
                    }}
                    country
                    site_type{{
                      name
                      value
                    }}
                    area
                    latitude
                    longitude
                    owner_id
                    owner_site_name
                    url
                    telenor_subscription_id
                    responsible_for{{
                      __typename
                      id
                      name
                    }}
                  }}
                }}
                located_in{{
                  __typename
                  id
                  name
                  ...on Firewall{{
                    operational_state{{
                      value
                    }}
                    ip_addresses
                  }}
                  ...on Switch{{
                    operational_state{{
                      value
                    }}
                    ip_addresses
                  }}
                }}
                has{{
                  __typename
                  id
                  name
                  ...on Rack{{
                    height
                    depth
                    width
                    rack_units
                  }}
                }}
              }}
            }}
            parent_site_updated{{
              errors{{
                field
                messages
              }}
              site{{
                id
                name
                country_code{{
                  name
                  value
                }}
                country
                site_type{{
                  name
                  value
                }}
                area
                latitude
                longitude
                owner_id
                owner_site_name
                url
                telenor_subscription_id
              }}
            }}
            located_in_firewall_updated{{
              errors{{
                field
                messages
              }}
              firewall{{
                id
                name
                operational_state{{
                  value
                }}
              }}
            }}
            located_in_switch_updated{{
              errors{{
                field
                messages
              }}
              switch{{
                id
                name
                operational_state{{
                  value
                }}
              }}
            }}
            {has_payload}{{
              errors{{
                field
                messages
              }}
              rack{{
                id
                name
                height
                depth
                width
                rack_units
              }}
            }}
          }}
        }}
        """

        query = query_t.format(
            main_input=main_input, main_input_id=main_input_id,
            has_input=has_input, has_input_id=has_input_id,
            main_payload=main_payload, has_payload=has_payload,
            room_name=room_name, room_floor=room_floor,
            has_rack_name=has_rack_name, has_rack_height=has_rack_height,
            has_rack_depth=has_rack_depth, has_rack_width=has_rack_width,
            has_rack_rack_units=has_rack_rack_units,
            parent_site_id=parent_site_id,
            parent_site_name=parent_site_name, parent_site_country=parent_site_country,
            parent_site_type=parent_site_type, parent_site_area=parent_site_area,
            parent_site_longitude=parent_site_longitude, parent_site_latitude=parent_site_latitude,
            parent_site_owner_id=parent_site_owner_id,
            parent_site_owner_site_name=parent_site_owner_site_name,
            parent_site_url=parent_site_url,
            parent_site_telenor_subscription_id=parent_site_telenor_subscription_id,
            responsible_for_id=responsible_for_id,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_room']
        created_errors = all_data[main_payload]['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        submutations = {
            'parent_site_updated': None,
            'located_in_firewall_updated': None,
            'located_in_switch_updated': None,
            has_payload: None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], pformat(submutations[k], indent=1)

        # check room data
        check_room = all_data[main_payload]['room']
        room_id = check_room['id']

        self.assertEquals(check_room['name'], room_name)
        self.assertEquals(check_room['floor'], room_floor)

        # check parent site data
        check_parent_site = all_data['parent_site_updated']['site']

        self.assertEquals(check_parent_site['id'], parent_site_id)
        self.assertEquals(check_parent_site['name'], parent_site_name)
        self.assertEquals(check_parent_site['country_code']['name'], parent_site_country)
        if parent_site_type:
            self.assertEquals(check_parent_site['site_type']['value'], parent_site_type)
        self.assertEquals(check_parent_site['area'], parent_site_area)
        self.assertEquals(check_parent_site['latitude'], parent_site_latitude)
        self.assertEquals(check_parent_site['longitude'], parent_site_longitude)
        self.assertEquals(check_parent_site['owner_id'], parent_site_owner_id)
        self.assertEquals(check_parent_site['owner_site_name'], parent_site_owner_site_name)
        self.assertEquals(check_parent_site['url'], parent_site_url)
        self.assertEquals(check_parent_site['telenor_subscription_id'], \
            parent_site_telenor_subscription_id)

        self.assertEquals(check_room['parent']['id'], parent_site_id)

        # check firewall
        check_firewall = all_data['located_in_firewall_updated'][0]['firewall']

        self.assertEquals(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEquals(check_room['located_in'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data['located_in_switch_updated'][0]['switch']

        self.assertEquals(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEquals(check_room['located_in'][1]['id'], switch_id)

        # check has rack
        check_has_rack = all_data[has_payload][0]['rack']
        has_rack_id = check_has_rack['id']

        self.assertEquals(check_has_rack['name'], has_rack_name)
        self.assertEquals(check_has_rack['height'], int(has_rack_height))
        self.assertEquals(check_has_rack['depth'], int(has_rack_depth))
        self.assertEquals(check_has_rack['width'], int(has_rack_width))
        self.assertEquals(check_has_rack['rack_units'], int(has_rack_rack_units))

        self.assertEquals(check_room['has'][0]['id'], has_rack_id)

        ## edition
        # data room
        a_room = data_generator.create_room(add_parent=False)
        room_name = a_room.get_node().data.get("name")
        room_floor = a_room.get_node().data.get("floor")
        a_room.delete()

        # has data rack
        has_rack = data_generator.create_rack(add_parent=False)
        has_rack_name = has_rack.get_node().data.get("name")
        has_rack_height = has_rack.get_node().data.get("height")
        has_rack_depth = has_rack.get_node().data.get("depth")
        has_rack_width = has_rack.get_node().data.get("width")
        has_rack_rack_units = has_rack.get_node().data.get("rack_units")
        has_rack.delete()

        # create a parent site
        parent_site = data_generator.create_site()
        parent_site_name = "New Parent Site"
        parent_site_country = parent_site.get_node().data.get("country")
        parent_site_type = parent_site.get_node().data.get("site_type")
        parent_site_type = '' if not parent_site_type else parent_site_type
        parent_site_area = parent_site.get_node().data.get("area")
        parent_site_longitude = parent_site.get_node().data.get("longitude")
        parent_site_latitude = parent_site.get_node().data.get("latitude")
        parent_site_owner_id = parent_site.get_node().data.get("owner_id")
        parent_site_owner_site_name = parent_site.get_node().data.get("owner_site_name")
        parent_site_url = parent_site.get_node().data.get("url")
        parent_site_telenor_subscription_id = parent_site.get_node().data.get("telenor_subscription_id")
        parent_site.delete()

        # create firewall
        firewall = data_generator.create_firewall()
        firewall_name = "Test firewall"
        firewall_opstate = firewall.get_node().data.get("operational_state")
        firewall.delete()

        # create switch
        switch = data_generator.create_switch()
        switch_name = "Test switch"
        switch_opstate = switch.get_node().data.get("operational_state")
        switch.delete()

        main_input = 'update_input'
        main_input_id = 'id: "{}"'.format(room_id)
        has_input = 'update_has_rack'
        has_input_id = 'id: "{}"'.format(has_rack_id)
        main_payload = 'updated'
        has_payload = 'has_rack_updated'

        query = query_t.format(
            main_input=main_input, main_input_id=main_input_id,
            has_input=has_input, has_input_id=has_input_id,
            main_payload=main_payload, has_payload=has_payload,
            room_name=room_name, room_floor=room_floor,
            has_rack_name=has_rack_name, has_rack_height=has_rack_height,
            has_rack_depth=has_rack_depth, has_rack_width=has_rack_width,
            has_rack_rack_units=has_rack_rack_units,
            parent_site_id=parent_site_id,
            parent_site_name=parent_site_name, parent_site_country=parent_site_country,
            parent_site_type=parent_site_type, parent_site_area=parent_site_area,
            parent_site_longitude=parent_site_longitude, parent_site_latitude=parent_site_latitude,
            parent_site_owner_id=parent_site_owner_id,
            parent_site_owner_site_name=parent_site_owner_site_name,
            parent_site_url=parent_site_url,
            parent_site_telenor_subscription_id=parent_site_telenor_subscription_id,
            responsible_for_id=responsible_for_id,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_room']
        updated_errors = all_data[main_payload]['errors']
        assert not updated_errors, pformat(updated_errors, indent=1)

        submutations = {
            'parent_site_updated': None,
            'located_in_firewall_updated': None,
            'located_in_switch_updated': None,
            has_payload: None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], pformat(submutations[k], indent=1)

        # check room data
        check_room = all_data[main_payload]['room']
        self.assertEquals(check_room['name'], room_name)
        self.assertEquals(check_room['floor'], room_floor)

        # check parent site data
        check_parent_site = all_data['parent_site_updated']['site']

        self.assertEquals(check_parent_site['id'], parent_site_id)
        self.assertEquals(check_parent_site['name'], parent_site_name)
        self.assertEquals(check_parent_site['country_code']['name'], parent_site_country)
        if parent_site_type:
            self.assertEquals(check_parent_site['site_type']['value'], parent_site_type)
        self.assertEquals(check_parent_site['area'], parent_site_area)
        self.assertEquals(check_parent_site['latitude'], parent_site_latitude)
        self.assertEquals(check_parent_site['longitude'], parent_site_longitude)
        self.assertEquals(check_parent_site['owner_id'], parent_site_owner_id)
        self.assertEquals(check_parent_site['owner_site_name'], parent_site_owner_site_name)
        self.assertEquals(check_parent_site['url'], parent_site_url)
        self.assertEquals(check_parent_site['telenor_subscription_id'], \
            parent_site_telenor_subscription_id)

        self.assertEquals(check_room['parent']['id'], parent_site_id)

        # check firewall
        check_firewall = all_data['located_in_firewall_updated'][0]['firewall']

        self.assertEquals(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEquals(check_room['located_in'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data['located_in_switch_updated'][0]['switch']

        self.assertEquals(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEquals(check_room['located_in'][1]['id'], switch_id)

        # check has rack
        check_has_rack = all_data[has_payload][0]['rack']
        has_rack_id = check_has_rack['id']

        self.assertEquals(check_has_rack['name'], has_rack_name)
        self.assertEquals(check_has_rack['height'], int(has_rack_height))
        self.assertEquals(check_has_rack['depth'], int(has_rack_depth))
        self.assertEquals(check_has_rack['width'], int(has_rack_width))
        self.assertEquals(check_has_rack['rack_units'], int(has_rack_rack_units))

        self.assertEquals(check_room['has'][0]['id'], has_rack_id)


class RackTest(Neo4jGraphQLNetworkTest):
    def test_rack(self):
        data_generator = NetworkFakeDataGenerator()

        ## creation
        # data rack
        a_rack = data_generator.create_rack(add_parent=False)
        rack_name = a_rack.get_node().data.get("name")
        rack_height = a_rack.get_node().data.get("height")
        rack_depth = a_rack.get_node().data.get("depth")
        rack_width = a_rack.get_node().data.get("width")
        rack_rack_units = a_rack.get_node().data.get("rack_units")
        a_rack.delete()

        # create a parent room
        parent_room = data_generator.create_room(add_parent=False)
        parent_room_id = relay.Node.to_global_id(str(parent_room.node_type),
                                                str(parent_room.handle_id))
        parent_room_name = parent_room.get_node().data.get("name")
        parent_room_floor = parent_room.get_node().data.get("floor")

        # create firewall
        firewall = data_generator.create_firewall()
        firewall_id = relay.Node.to_global_id(str(firewall.node_type),
                                            str(firewall.handle_id))
        firewall_name = "Test firewall"
        firewall_opstate = firewall.get_node().data.get("operational_state")

        # create switch
        switch = data_generator.create_switch()
        switch_id = relay.Node.to_global_id(str(switch.node_type),
                                            str(switch.handle_id))
        switch_name = "Test switch"
        switch_opstate = switch.get_node().data.get("operational_state")

        main_input = "create_input"
        main_input_id = ""
        main_payload = 'created'

        firewall_rackback = 'true'
        switch_rackback = 'false'

        query_t = """
        mutation{{
          composite_rack(input:{{
            {main_input}:{{
              {main_input_id}
              name: "{rack_name}"
              height: {rack_height}
              depth: {rack_depth}
              width: {rack_width}
              rack_units: {rack_rack_units}
            }}
            update_parent_room:{{
              id: "{parent_room_id}"
              name: "{parent_room_name}"
              floor: "{parent_room_floor}"
            }}
            update_located_in_firewall:[
              {{
                id: "{firewall_id}"
                name: "{firewall_name}"
                operational_state: "{firewall_opstate}"
                rack_back: {firewall_rackback}
              }}
            ]
            update_located_in_switch:[
              {{
                id: "{switch_id}"
                name: "{switch_name}"
                operational_state: "{switch_opstate}"
                rack_back: {switch_rackback}
              }}
            ]
          }}){{
            {main_payload}{{
              errors{{
                field
                messages
              }}
              rack{{
                id
                name
                height
                depth
                width
                rack_units
                parent{{
                  ...on Room{{
                    id
                    name
                    floor
                  }}
                }}
                front{{
                  ...on Switch{{
                    id
                    name
                    operational_state{{
                      value
                    }}
                  }}
                  ...on Firewall{{
                    id
                    name
                    operational_state{{
                      value
                    }}
                  }}
                }}
                back{{
                  ...on Switch{{
                    id
                    name
                    operational_state{{
                      value
                    }}
                  }}
                  ...on Firewall{{
                    id
                    name
                    operational_state{{
                      value
                    }}
                  }}
                }}
              }}
            }}
            located_in_firewall_updated{{
              errors{{
                field
                messages
              }}
              firewall{{
                id
                name
                operational_state{{
                  value
                }}
                rack_back
              }}
            }}
            located_in_switch_updated{{
              errors{{
                field
                messages
              }}
              switch{{
                id
                name
                operational_state{{
                  value
                }}
                rack_back
              }}
            }}
            parent_room_updated{{
              errors{{
                field
                messages
              }}
              room{{
                id
                name
                floor
              }}
            }}
          }}
        }}
        """

        query = query_t.format(
            main_input=main_input, main_input_id=main_input_id,
            main_payload=main_payload,
            rack_name=rack_name, rack_height=rack_height, rack_depth=rack_depth,
            rack_width=rack_width, rack_rack_units=rack_rack_units,
            parent_room_id=parent_room_id, parent_room_name=parent_room_name,
            parent_room_floor=parent_room_floor,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            firewall_rackback=firewall_rackback,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
            switch_rackback=switch_rackback,
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_rack']
        created_errors = all_data[main_payload]['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        submutations = {
            'parent_room_updated': None,
            'located_in_firewall_updated': None,
            'located_in_switch_updated': None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], pformat(submutations[k], indent=1)

        # check rack data
        check_rack = all_data[main_payload]['rack']
        rack_id = check_rack['id']

        self.assertEquals(check_rack['name'], rack_name)
        self.assertEquals(check_rack['height'], int(rack_height))
        self.assertEquals(check_rack['depth'], int(rack_depth))
        self.assertEquals(check_rack['width'], int(rack_width))
        self.assertEquals(check_rack['rack_units'], int(rack_rack_units))

        # check parent room data
        check_parent_room = all_data['parent_room_updated']['room']

        self.assertEquals(check_parent_room['id'], parent_room_id)
        self.assertEquals(check_parent_room['name'], parent_room_name)
        self.assertEquals(check_parent_room['floor'], parent_room_floor)

        self.assertEquals(check_rack['parent']['id'], parent_room_id)

        # check firewall
        check_firewall = all_data['located_in_firewall_updated'][0]['firewall']

        self.assertEquals(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEquals(check_rack['back'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data['located_in_switch_updated'][0]['switch']

        self.assertEquals(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEquals(check_rack['front'][0]['id'], switch_id)

        ## update
        # data rack
        a_rack = data_generator.create_rack(add_parent=False)
        rack_name = a_rack.get_node().data.get("name")
        rack_height = a_rack.get_node().data.get("height")
        rack_depth = a_rack.get_node().data.get("depth")
        rack_width = a_rack.get_node().data.get("width")
        rack_rack_units = a_rack.get_node().data.get("rack_units")
        a_rack.delete()

        # create a parent room
        parent_room = data_generator.create_room(add_parent=False)
        parent_room_id = relay.Node.to_global_id(str(parent_room.node_type),
                                                str(parent_room.handle_id))
        parent_room_name = parent_room.get_node().data.get("name")
        parent_room_floor = parent_room.get_node().data.get("floor")

        # firewall and switch back reversed
        firewall_rackback = 'false'
        switch_rackback = 'true'

        main_input = "update_input"
        main_input_id = 'id: "{}"'.format(rack_id)
        main_payload = 'updated'

        query = query_t.format(
            main_input=main_input, main_input_id=main_input_id,
            main_payload=main_payload,
            rack_name=rack_name, rack_height=rack_height, rack_depth=rack_depth,
            rack_width=rack_width, rack_rack_units=rack_rack_units,
            parent_room_id=parent_room_id, parent_room_name=parent_room_name,
            parent_room_floor=parent_room_floor,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            firewall_rackback=firewall_rackback,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
            switch_rackback=switch_rackback,
        )

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_rack']
        created_errors = all_data[main_payload]['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        submutations = {
            'parent_room_updated': None,
            'located_in_firewall_updated': None,
            'located_in_switch_updated': None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], pformat(submutations[k], indent=1)

        # check rack data
        check_rack = all_data[main_payload]['rack']

        self.assertEquals(check_rack['name'], rack_name)
        self.assertEquals(check_rack['height'], int(rack_height))
        self.assertEquals(check_rack['depth'], int(rack_depth))
        self.assertEquals(check_rack['width'], int(rack_width))
        self.assertEquals(check_rack['rack_units'], int(rack_rack_units))

        # check parent room data
        check_parent_room = all_data['parent_room_updated']['room']

        self.assertEquals(check_parent_room['id'], parent_room_id)
        self.assertEquals(check_parent_room['name'], parent_room_name)
        self.assertEquals(check_parent_room['floor'], parent_room_floor)

        self.assertEquals(check_rack['parent']['id'], parent_room_id)

        # check firewall
        check_firewall = all_data['located_in_firewall_updated'][0]['firewall']

        self.assertEquals(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEquals(check_rack['front'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data['located_in_switch_updated'][0]['switch']

        self.assertEquals(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEquals(check_rack['back'][0]['id'], switch_id)


class ServiceTest(Neo4jGraphQLNetworkTest):
    def test_service(self):
        data_generator = NetworkFakeDataGenerator()

        ## creation
        # data service
        a_service = data_generator.create_service()
        srv_name = a_service.get_node().data.get("name")
        srv_service_type = a_service.get_node().data\
            .get("service_type")
        srv_operational_state = a_service.get_node().data\
            .get("operational_state")
        srv_description = a_service.get_node().data.get("description")
        srv_project_end_date = a_service.get_node().data\
            .get("project_end_date", None)
        srv_decommissioned_date = a_service.get_node().data\
            .get("decommissioned_date", None)

        # get provider
        incoming = a_service.get_node()._incoming()
        provider = NodeHandle.objects.get(handle_id=\
                        incoming['Provides'][0]['node'].handle_id)
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # get support and responsible groups
        group_s = NodeHandle.objects.get(handle_id=\
                        incoming['Supports'][0]['node'].handle_id)
        group_r = NodeHandle.objects.get(handle_id=\
                        incoming['Takes_responsibility'][0]['node'].handle_id)

        group_support_id = relay.Node.to_global_id(str(group_s.node_type),
                                            str(group_s.handle_id))
        group_responsible_id = relay.Node.to_global_id(str(group_r.node_type),
                                            str(group_r.handle_id))

        # dependencies
        # create firewall
        firewall = data_generator.create_firewall()
        firewall_id = relay.Node.to_global_id(str(firewall.node_type),
                                            str(firewall.handle_id))
        firewall_name = "Test firewall"
        firewall_opstate = firewall.get_node().data.get("operational_state")

        # create switch
        switch = data_generator.create_switch()
        switch_id = relay.Node.to_global_id(str(switch.node_type),
                                            str(switch.handle_id))
        switch_name = "Test switch"
        switch_opstate = switch.get_node().data.get("operational_state")

        # users
        # create customer
        customer = data_generator.create_customer()
        customer_id = relay.Node.to_global_id(str(customer.node_type),
                                            str(customer.handle_id))
        customer_name = customer.get_node().data.get("name")
        customer_url = customer.get_node().data.get("url")
        customer_description = customer.get_node().data.get("description")

        # create end user
        enduser = data_generator.create_end_user()
        enduser_id = relay.Node.to_global_id(str(enduser.node_type.type\
                                                    .replace(' ', '')),
                                            str(enduser.handle_id))
        enduser_name = enduser.get_node().data.get("name")
        enduser_url = enduser.get_node().data.get("url")
        enduser_description = enduser.get_node().data.get("description")

        main_input = "create_input"
        main_input_id = ""
        main_payload = 'created'

        if srv_project_end_date:
            srv_project_end_date = srv_project_end_date.split("T")[0]

        if srv_decommissioned_date:
            srv_decommissioned_date = srv_decommissioned_date.split("T")[0]

        project_end_date = "" if not srv_project_end_date else \
                    'project_end_date: "{}"'.format(srv_project_end_date)
        decommissioned_date = "" if not srv_decommissioned_date else \
                    'decommissioned_date: "{}"'.format(srv_decommissioned_date)

        query_t = """
        mutation{{
          composite_service(input:{{
            {main_input}:{{
              {main_input_id}
              name: "{srv_name}"
              service_type: "{srv_service_type}"
              operational_state: "{srv_operational_state}"
              description: "{srv_description}"
              relationship_provider: "{provider_id}"
              {project_end_date}
              {decommissioned_date}
            }}
            update_dependencies_firewall:[
              {{
                id: "{firewall_id}"
                name: "{firewall_name}"
                operational_state: "{firewall_opstate}"
              }}
            ]
            update_dependencies_switch:[
              {{
                id: "{switch_id}"
                name: "{switch_name}"
                operational_state: "{switch_opstate}"
              }}
            ]
            update_used_by_customer: [{{
              id: "{customer_id}"
              name: "{customer_name}"
              url: "{customer_url}"
              description: "{customer_description}"
            }}]
            update_used_by_enduser: [{{
              id: "{enduser_id}"
              name: "{enduser_name}"
              url: "{enduser_url}"
              description: "{enduser_description}"
            }}]
          }}){{
            {main_payload}{{
              errors{{
                field
                messages
              }}
              service{{
                id
                name
                operational_state{{
                  value
                }}
                service_type{{
                  name
                }}
                description
                project_end_date
                decommissioned_date
                dependencies{{
                  id
                  name
                }}
                used_by{{
                  id
                  name
                }}
                provider{{
                  id
                  name
                }}
                customers{{
                  id
                  name
                }}
                end_users{{
                  id
                  name
                }}
              }}
            }}
            dependencies_firewall_updated{{
              errors{{
                field
                messages
              }}
              firewall{{
                id
                name
                operational_state{{
                  value
                }}
                rack_back
              }}
            }}
            dependencies_switch_updated{{
              errors{{
                field
                messages
              }}
              switch{{
                id
                name
                operational_state{{
                  value
                }}
                rack_back
              }}
            }}
            used_by_customer_updated{{
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
            used_by_enduser_updated{{
              errors{{
                field
                messages
              }}
              endUser{{
                id
                name
                url
                description
              }}
            }}
          }}
        }}
        """

        query = query_t.format(main_input=main_input,
            main_input_id=main_input_id, main_payload=main_payload,
            srv_name=srv_name, srv_operational_state=srv_operational_state,
            srv_description=srv_description, srv_service_type=srv_service_type,
            project_end_date=project_end_date,
            decommissioned_date=decommissioned_date,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
            customer_id=customer_id, customer_name=customer_name,
            customer_url=customer_url,
            customer_description=customer_description,
            enduser_id=enduser_id, enduser_name=enduser_name,
            enduser_url=enduser_url,
            enduser_description=enduser_description,
            provider_id=provider_id,
        )

        a_service.delete()

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_service']
        created_errors = all_data[main_payload]['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        submutations = {
            'dependencies_firewall_updated': None,
            'dependencies_switch_updated': None,
            'used_by_customer_updated': None,
            'used_by_enduser_updated': None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], pformat(submutations[k], indent=1)

        # check service data
        check_service = all_data[main_payload]['service']
        service_id = check_service['id']

        self.assertEquals(check_service['name'], srv_name)
        self.assertEquals(check_service['operational_state']['value'],
                            srv_operational_state)
        self.assertEquals(check_service['description'], srv_description)
        self.assertEquals(check_service['service_type']['name'], srv_service_type)

        # check customer
        check_customer = all_data['used_by_customer_updated'][0]['customer']

        self.assertEqualIds(check_customer['id'], customer_id)
        self.assertEquals(check_customer['name'], customer_name)
        self.assertEquals(check_customer['url'], customer_url)
        self.assertEquals(check_customer['description'], customer_description)
        self.assertEqualIds(check_service['used_by'][0]['id'], customer_id)
        self.assertEqualIds(check_service['customers'][0]['id'], customer_id)

        # check end user
        check_enduser = all_data['used_by_enduser_updated'][0]['endUser']

        self.assertEqualIds(check_enduser['id'], enduser_id)
        self.assertEquals(check_enduser['name'], enduser_name)
        self.assertEquals(check_enduser['url'], enduser_url)
        self.assertEquals(check_enduser['description'], enduser_description)
        self.assertEqualIds(check_service['used_by'][1]['id'], enduser_id)
        self.assertEqualIds(check_service['end_users'][0]['id'], enduser_id)

        # check firewall
        check_firewall = all_data['dependencies_firewall_updated'][0]['firewall']

        self.assertEqualIds(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEqualIds(check_service['dependencies'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data['dependencies_switch_updated'][0]['switch']

        self.assertEqualIds(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEqualIds(check_service['dependencies'][1]['id'], switch_id)

        # check provider
        check_provider = check_service['provider']
        self.assertEqualIds(check_provider['id'], provider_id)

        ## update
        # data service
        a_service = data_generator.create_service()
        srv_name = a_service.get_node().data.get("name")
        srv_service_type = a_service.get_node().data\
            .get("service_type")
        srv_operational_state = a_service.get_node().data\
            .get("operational_state")
        srv_description = a_service.get_node().data.get("description")
        srv_project_end_date = a_service.get_node().data\
            .get("project_end_date", None)
        srv_decommissioned_date = a_service.get_node().data\
            .get("decommissioned_date", None)

        # get provider
        incoming = a_service.get_node()._incoming()
        provider = NodeHandle.objects.get(handle_id=\
                        incoming['Provides'][0]['node'].handle_id)
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # get support and responsible groups
        group_s = NodeHandle.objects.get(handle_id=\
                        incoming['Supports'][0]['node'].handle_id)
        group_r = NodeHandle.objects.get(handle_id=\
                        incoming['Takes_responsibility'][0]['node'].handle_id)

        group_support_id = relay.Node.to_global_id(str(group_s.node_type),
                                            str(group_s.handle_id))
        group_responsible_id = relay.Node.to_global_id(str(group_r.node_type),
                                            str(group_r.handle_id))

        # dependencies
        # create firewall
        firewall = data_generator.create_firewall()
        firewall_name = "Test firewall"
        firewall_opstate = firewall.get_node().data.get("operational_state")
        firewall.delete()

        # create switch
        switch = data_generator.create_switch()
        switch_name = "Test switch"
        switch_opstate = switch.get_node().data.get("operational_state")
        switch.delete()

        # users
        # create customer
        customer = data_generator.create_customer()
        customer_name = customer.get_node().data.get("name")
        customer_url = customer.get_node().data.get("url")
        customer_description = customer.get_node().data.get("description")
        customer.delete()

        # create end user
        enduser = data_generator.create_end_user()
        enduser_name = enduser.get_node().data.get("name")
        enduser_url = enduser.get_node().data.get("url")
        enduser_description = enduser.get_node().data.get("description")
        enduser.delete()

        main_input = "update_input"
        main_input_id = 'id: "{}"'.format(service_id)
        main_payload = 'updated'

        if srv_project_end_date:
            srv_project_end_date = srv_project_end_date.split("T")[0]

        if srv_decommissioned_date:
            srv_decommissioned_date = srv_decommissioned_date.split("T")[0]

        project_end_date = "" if not srv_project_end_date else \
                    'project_end_date: "{}"'.format(srv_project_end_date)
        decommissioned_date = "" if not srv_decommissioned_date else \
                    'decommissioned_date: "{}"'.format(srv_decommissioned_date)

        query = query_t.format(main_input=main_input,
            main_input_id=main_input_id, main_payload=main_payload,
            srv_name=srv_name, srv_operational_state=srv_operational_state,
            srv_description=srv_description, srv_service_type=srv_service_type,
            project_end_date=project_end_date,
            decommissioned_date=decommissioned_date,
            firewall_id=firewall_id, firewall_name=firewall_name,
            firewall_opstate=firewall_opstate,
            switch_id=switch_id, switch_name=switch_name,
            switch_opstate=switch_opstate,
            customer_id=customer_id, customer_name=customer_name,
            customer_url=customer_url,
            customer_description=customer_description,
            enduser_id=enduser_id, enduser_name=enduser_name,
            enduser_url=enduser_url,
            enduser_description=enduser_description,
            provider_id=provider_id,
        )

        a_service.delete()

        result = schema.execute(query, context=self.context)
        assert not result.errors, pformat(result.errors, indent=1)

        # check for errors
        all_data = result.data['composite_service']
        created_errors = all_data[main_payload]['errors']
        assert not created_errors, pformat(created_errors, indent=1)

        submutations = {
            'dependencies_firewall_updated': None,
            'dependencies_switch_updated': None,
            'used_by_customer_updated': None,
            'used_by_enduser_updated': None,
        }

        for k,v in submutations.items():
            if all_data[k]:
                item = None

                try:
                    all_data[k][0]
                    for item in all_data[k]:
                        submutations[k] = item['errors']
                        assert not submutations[k], pformat(submutations[k], indent=1)
                except KeyError:
                    item = all_data[k]
                    submutations[k] = item['errors']
                    assert not submutations[k], pformat(submutations[k], indent=1)

        # check service data
        check_service = all_data[main_payload]['service']
        service_id = check_service['id']

        self.assertEquals(check_service['name'], srv_name)
        self.assertEquals(check_service['operational_state']['value'],
                            srv_operational_state)
        self.assertEquals(check_service['description'], srv_description)
        self.assertEquals(check_service['service_type']['name'], srv_service_type)

        # check customer
        check_customer = all_data['used_by_customer_updated'][0]['customer']

        self.assertEqualIds(check_customer['id'], customer_id)
        self.assertEquals(check_customer['name'], customer_name)
        self.assertEquals(check_customer['url'], customer_url)
        self.assertEquals(check_customer['description'], customer_description)
        self.assertEqualIds(check_service['used_by'][0]['id'], customer_id)

        # check end user
        check_enduser = all_data['used_by_enduser_updated'][0]['endUser']

        self.assertEqualIds(check_enduser['id'], enduser_id)
        self.assertEquals(check_enduser['name'], enduser_name)
        self.assertEquals(check_enduser['url'], enduser_url)
        self.assertEquals(check_enduser['description'], enduser_description)
        self.assertEqualIds(check_service['used_by'][1]['id'], enduser_id)

        # check firewall
        check_firewall = all_data['dependencies_firewall_updated'][0]['firewall']

        self.assertEqualIds(check_firewall['id'], firewall_id)
        self.assertEquals(check_firewall['name'], firewall_name)
        self.assertEquals(check_firewall['operational_state']['value'],
                            firewall_opstate)
        self.assertEqualIds(check_service['dependencies'][0]['id'], firewall_id)

        # check switch
        check_switch = all_data['dependencies_switch_updated'][0]['switch']

        self.assertEqualIds(check_switch['id'], switch_id)
        self.assertEquals(check_switch['name'], switch_name)
        self.assertEquals(check_switch['operational_state']['value'],
                            switch_opstate)
        self.assertEqualIds(check_service['dependencies'][1]['id'], switch_id)

        # check provider
        check_provider = check_service['provider']
        self.assertEqualIds(check_provider['id'], provider_id)
