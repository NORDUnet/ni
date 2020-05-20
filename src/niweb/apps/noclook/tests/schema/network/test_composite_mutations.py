# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.models import NodeHandle, Dropdown, Choice, Group, \
    GroupContextAuthzAction, NodeHandleContext
from collections import OrderedDict
from . import Neo4jGraphQLNetworkTest
from niweb.schema import schema
from pprint import pformat
from graphene import relay

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
