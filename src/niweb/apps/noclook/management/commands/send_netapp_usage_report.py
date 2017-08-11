# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
import tempfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from decimal import Decimal, ROUND_DOWN
from apps.noclook import helpers
import norduniclient as nc

class Command(BaseCommand):
    help = 'Sends netapp usage report for services specified in settings/secrets.py'

    def handle(self, *args, **options):
        to = getattr(django_settings, 'REPORTS_TO', [])
        cc = getattr(django_settings, 'REPORTS_CC', None)
        bcc = getattr(django_settings, 'REPORTS_BCC', None)
        extra_report = getattr(django_settings, 'EXTRA_REPORT_TO', {})
        free_gb = Decimal('1000.00')
        price_per_gb = Decimal('0.40')
        quarter_month_map = {
            1: ['01', '02', '03'],
            2: ['04', '05', '06'],
            3: ['07', '08', '09'],
            4: ['10', '11', '12']
        }
        utcnow = datetime.utcnow()
        last_month = utcnow - relativedelta(months=1)
        year = str(last_month.year)
        last_quarter = (last_month.month - 1) // 3 + 1
        services = getattr(django_settings, 'NETAPP_REPORT_SETTINGS', [])
        for service in services:
            report_data = []
            service_node = nc.get_unique_node_by_name(nc.graphdb.manager, service['service_id'], 'Service')
            customers = [item['node'].data.get('name', '') for item in
                         service_node.get_customers().get('customers', [])]
            customers = ', '.join(customers)
            data_dict = json.loads(service_node.data.get('netapp_storage_monthly', '{}')).get(year, None)
            if data_dict:
                for month in quarter_month_map[last_quarter]:
                    key = '%s-%s' % (year, month)
                    report_data.append({key: data_dict.get(month.lstrip('0'), 0.0)})
                # Create and send the mail
                subject = 'Storage cost for %s Q%d %s' % (service['contract_reference'], last_quarter, year)
                heading = 'Adobe connect storage volume billing Q%d, %s, for %s.' % (last_quarter, year, customers)
                body = '''
                This is an auto generated report from NOCLook for service ID %s.

                %s

                This report was generated on %s UTC.
                    ''' % (service['service_id'], heading, utcnow.strftime('%Y-%m-%d %H:%M'))
                extended_to = to + extra_report.get(service['service_id'], [])  # Avoid changing REPORTS_TO :)
                filename = 'Storage cost for %s Q%d %s.xls' % (service['contract_reference'], last_quarter, year)
                wb = helpers.dicts_to_xls({}, [], '%s Q%d %s' % (service['service_id'], last_quarter, year))
                # Calculate and write pricing info
                ws = wb.get_sheet(0)
                ws.write(1, 1, heading)
                ws.write(2, 1, 'Reference: %s' % service['contract_reference'])
                ws.write(4, 1, 'Month')
                ws.write(4, 2, 'Storage (GB)')
                ws.write(4, 3, 'Service inc.')
                ws.write(4, 4, 'Billable storage')
                ws.write(4, 5, u'Price per GB (€)')
                ws.write(4, 6, u'Monthly cost (€)')
                total_cost = Decimal(0)
                for i in range(0, len(report_data)):
                    row = 5 + i
                    storage_month = Decimal(report_data[i].values()[0])
                    billable = Decimal(max(storage_month - free_gb, 0))
                    cost_month = billable * price_per_gb
                    total_cost += cost_month
                    ws.write(row, 1, list(report_data[i].keys())[0])
                    ws.write(row, 2, storage_month.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                    ws.write(row, 3, -free_gb.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                    ws.write(row, 4, billable.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                    ws.write(row, 5, price_per_gb.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                    ws.write(row, 6, cost_month.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                ws.write(9, 1, 'Quarterly storage cost')
                ws.write(9, 6, total_cost.quantize(Decimal('.01'), rounding=ROUND_DOWN))
                with tempfile.TemporaryFile() as temp:
                    wb.save(temp)
                    temp.seek(0)
                    msg = helpers.create_email(subject, body, extended_to, cc, bcc, temp.read(), filename,
                                               'application/excel')
                    msg.send()
            self.stdout.write('Sent netapp usage report for service {}.'.format(service['service_id']))
