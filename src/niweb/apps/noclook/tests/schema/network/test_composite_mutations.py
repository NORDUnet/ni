# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, Dropdown, Choice, Group, \
    GroupContextAuthzAction, NodeHandleContext, SwitchType
from apps.noclook.tests.stressload.data_generator \
    import NetworkFakeDataGenerator, CommunityFakeDataGenerator
from collections import OrderedDict
from . import Neo4jGraphQLNetworkTest
from niweb.schema import schema
from pprint import pformat
from graphene import relay

import random

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
        generator = NetworkFakeDataGenerator()
        provider = generator.create_provider()
        provider_id = relay.Node.to_global_id(str(provider.node_type),
                                            str(provider.handle_id))

        # Create query
        query = '''
        mutation{{
          composite_cable(input:{{
            create_input:{{
              name: "{cable_name}"
              cable_type: "{cable_type}"
              description: "{cable_description}"
              relationship_provider: "{provider_id}"
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
                    bport_description=bport_description, provider_id=provider_id)

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

            query = '''
            mutation{{
              composite_cable(input:{{
                update_input:{{
                  id: "{cable_id}"
                  name: "{cable_name}"
                  cable_type: "{cable_type}"
                  description: "{cable_description}"
                  relationship_provider: "{provider_id}"
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
                        aport_id=aport_id, bport_id=bport_id, provider_id=provider_id)

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
        managed_by = random.choice(
            Dropdown.objects.get(name="host_management_sw").as_choices()[1:][1]
        )
        backup = "Manual script"
        os = "GNU/Linux"
        os_version = "5.8"
        contract_number = "001"
        max_number_of_ports = 20

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
              }}
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
                    max_number_of_ports=max_number_of_ports)

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
        self.assertEqual(created_switch['ip_addresses'], ip_addresses)
        self.assertEqual(created_switch['managed_by']['value'], managed_by)
        self.assertEqual(created_switch['backup'], backup)
        self.assertEqual(created_switch['os'], os)
        self.assertEqual(created_switch['os_version'], os_version)
        self.assertEqual(created_switch['contract_number'], contract_number)
        self.assertEqual(created_switch['max_number_of_ports'], max_number_of_ports)

        # check provider
        check_provider = created_switch['provider']
        self.assertEqual(check_provider['id'], provider_id)

        # check responsible group
        check_responsible = created_switch['responsible_group']
        self.assertEqual(check_responsible['id'], group1_id)

        # check support group
        check_support = created_switch['support_group']
        self.assertEqual(check_support['id'], group2_id)

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
        managed_by = random.choice(
            Dropdown.objects.get(name="host_management_sw").as_choices()[1:][1]
        )
        backup = "Jenkins script"
        os = "Linux"
        os_version = "5.7"
        contract_number = "002"
        max_number_of_ports = 15

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
                relationship_provider: "{provider_id}"
                responsible_group: "{group2_id}"
                support_group: "{group1_id}"
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
                description
                ip_addresses
                rack_units
                rack_position
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
                    max_number_of_ports=max_number_of_ports)

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
        self.assertEqual(updated_switch['ip_addresses'], ip_addresses)
        self.assertEqual(updated_switch['managed_by']['value'], managed_by)
        self.assertEqual(updated_switch['backup'], backup)
        self.assertEqual(updated_switch['os'], os)
        self.assertEqual(updated_switch['os_version'], os_version)
        self.assertEqual(updated_switch['contract_number'], contract_number)
        self.assertEqual(updated_switch['max_number_of_ports'], max_number_of_ports)

        # check provider
        check_provider = updated_switch['provider']
        self.assertEqual(check_provider['id'], provider_id)

        # check responsible group
        check_responsible = updated_switch['responsible_group']
        self.assertEqual(check_responsible['id'], group2_id)

        # check support group
        check_support = updated_switch['support_group']
        self.assertEqual(check_support['id'], group1_id)


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
        rack_units = random.randint(1,10)
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

        query = '''
        mutation{{
          composite_router(input:{{
            update_input:{{
              id: "{router_id}"
              description: "{description}"
              operational_state: "{operational_state}"
              rack_units: {rack_units}
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
                    port_1_name=port_1_name, port_1_type=port_1_type,
                    port_1_description=port_1_description,
                    port_2_id=port_2_id, port_2_name=port_2_name,
                    port_2_type=port_2_type,
                    port_2_description=port_2_description)

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
        self.assertEqual(updated_router['ports'][1]['id'], port_1_id)
        self.assertEqual(updated_router['ports'][0]['id'], port_2_id)
