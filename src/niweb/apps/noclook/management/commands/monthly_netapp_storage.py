# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
from apps.noclook import helpers
import norduniclient as nc


class Command(BaseCommand):

    def handle(self, *args, **options):
        user = User.objects.get(username='noclook')
        utcnow = datetime.utcnow()
        last_month = utcnow - relativedelta(months=1)
        services = getattr(django_settings, 'NETAPP_REPORT_SETTINGS', [])
        for service in services:
            service_node = nc.get_unique_node_by_name(nc.graphdb.manager, service['service_id'], 'Service')
            monthly_dict = json.loads(service_node.data.get('netapp_storage_monthly', '{}'))
            monthly_dict.setdefault(str(last_month.year), {})[str(last_month.month)] = \
                service_node.data.get('netapp_storage_sum', 0.0)
            property_dict = {'netapp_storage_monthly': json.dumps(monthly_dict)}
            helpers.dict_update_node(user, service_node.handle_id, property_dict, property_dict.keys())
            self.stdout.write('Monthly netapp usage stored for service {}.'.format(service['service_id']))
