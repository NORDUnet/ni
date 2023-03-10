# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import yesno, date
from django.conf import settings as django_settings
import tempfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
from apps.noclook.templatetags.noclook_tags import timestamp_to_td
from apps.noclook import helpers
import norduniclient as nc


class Command(BaseCommand):
    help = 'Sends host usage report for specified contract numbers.'

    def add_arguments(self, parser):
        parser.add_argument('contract_number', nargs='+', type=str)

    def handle(self, *args, **options):
        for contract_number in options['contract_number']:
            utcnow = datetime.utcnow()
            last_month = utcnow - relativedelta(months=1)
            subject = 'NOCLook host report for %s' % contract_number
            to = getattr(django_settings, 'REPORTS_TO', [])
            cc = getattr(django_settings, 'REPORTS_CC', None)
            bcc = getattr(django_settings, 'REPORTS_BCC', None)
            extra_report = getattr(django_settings, 'EXTRA_REPORT_TO', {})
            extended_to = to + extra_report.get(contract_number, [])  # Avoid changing REPORTS_TO :)
            body = '''
                This is an auto generated report from NOCLook for contract number %s.

                This report was generated on %s UTC.
                    ''' % (contract_number, utcnow.strftime('%Y-%m-%d %H:%M'))
            price_per_host = 95
            header = [
                'Host user',
                'Host',
                'Host type',
                'IP address(es)',
                'Contract number',
                'Description',
                'Responsible',
                'Backup',
                'Syslog',
                'Nagios',
                'Operational State',
                'Security Class',
                'Location',
                'Last seen',
                'Uptime (days)'
            ]
            result = []
            q = '''
                    MATCH (host_user:Host_User)-[r:Uses|Owns]->(host:Host)
                    WHERE host.contract_number = $contract_number
                    RETURN host_user.name as host_user_name, host.name, host.handle_id as host_handle_id
                    ORDER BY host_user.name, host.name
                    '''
            for item in nc.query_to_list(nc.graphdb.manager, q, contract_number=contract_number):
                host = nc.get_node_model(nc.graphdb.manager, item['host_handle_id'])
                age = helpers.neo4j_report_age(host.data, 15, 30)
                operational_state = host.data.get('operational_state', 'Not set')
                host_type = host.meta_type
                host_user = item['host_user_name']
                uptime = host.data.get('uptime', '')
                if uptime:
                    uptime = timestamp_to_td(uptime).days
                if host_type == 'Logical' and age != 'very_old' and operational_state != 'Decommissioned':
                    values = [
                        u'{}'.format(host_user),
                        u'{}'.format(host.data['name']),
                        u'{}'.format(host_type).capitalize(),
                        u', '.join([address for address in host.data['ip_addresses']]),
                        u'{}'.format(host.data['contract_number']),
                        u'{}'.format(host.data.get('description', '')),
                        u'{}'.format(host.data.get('responsible_group', '')),
                        u'{}'.format(host.data.get('backup', 'Not set')),
                        u'{}'.format(yesno(host.data.get('syslog', None), 'Yes,No,Not set')),
                        u'{}'.format(yesno(host.data.get('nagios_checks', False), 'Yes,No,Not set')),
                        u'{}'.format(operational_state),
                        u'{}'.format(host.data.get('security_class', '')),
                        u'{}'.format(''),
                        u'{}'.format(date(helpers.isots_to_dt(host.data), "Y-m-d")),
                        u'{}'.format(uptime),
                    ]
                    result.append(dict(zip(header, values)))
            num_hosts = len(result)
            filename = '%s hosts %s.xls' % (contract_number, last_month.strftime('%B %Y'))
            wb = helpers.dicts_to_xls(result, header, contract_number)
            # Calculate and write pricing info
            ws = wb.get_sheet(0)
            ws.write(num_hosts + 2, 1, 'Number of Virtual Servers')
            ws.write(num_hosts + 2, 4, '%d' % num_hosts)
            ws.write(num_hosts + 3, 1, 'Price')
            ws.write(num_hosts + 3, 4, '%d' % price_per_host)
            ws.write(num_hosts + 4, 1, 'Total Invoice amount ex. VAT')
            ws.write(num_hosts + 4, 4, '%d' % (num_hosts * price_per_host))
            with tempfile.TemporaryFile() as temp:
                wb.save(temp)
                temp.seek(0)
                msg = helpers.create_email(subject, body, extended_to, cc, bcc, temp.read(), filename, 'application/excel')
                msg.send()
            self.stdout.write('Sent report for contract number {}'.format(contract_number))
