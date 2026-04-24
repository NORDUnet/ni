from django.core.management import call_command
from ..neo4j_base import NeoTestCase
from apps.noclook import helpers
from django.core import mail


class SendHostReportTest(NeoTestCase):

    def test_send_host_report(self):
        host_user = self.create_node('Test co', 'host-user', 'Relation')
        host = self.create_node('sweet_host.test.dev', 'host', 'Logical')
        host_node = host.get_node()
        host_node.set_user(host_user.handle_id)

        host_data = {
            'description': 'Nice host',
            'responsible_group': 'DEV',
            'contract_number': 'DEV_TEST',
            'ip_addresses': '10.0.0.2',
            'backup': 'tsm',
            'uptime': 299764,
            'nagios_checks': 'PING',
            'operational_state': 'In service',
        }

        helpers.dict_update_node(self.user, host.handle_id, host_data)
        # Setup done

        call_command('send_host_usage_report', 'DEV_TEST')
        # Check if mail was sent..
        self.assertEqual(len(mail.outbox), 1)
        _mail = mail.outbox[0]
        self.assertEqual(len(_mail.attachments), 1, 'Should have 1 attachment')
        attachment = _mail.attachments[0]
        self.assertIn('DEV_TEST hosts', attachment[0])
        self.assertIn('.xls', attachment[0])
        # need to decode xls to see if values are correct
