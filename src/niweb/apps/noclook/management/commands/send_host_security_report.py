# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from datetime import datetime
from apps.noclook import helpers
import norduniclient as nc


class Command(BaseCommand):
    help = 'Sends host security report'

    def handle(self, *args, **options):
        unauthorized_q = """
            MATCH (host:Host)
            MATCH host<-[r:Depends_on]-()
            WHERE not(host.operational_state = "Decommissioned") and has(r.rogue_port)
            RETURN count(DISTINCT host) as unauthorized_host_count, count(r) as unauthorized_port_count
            """
        public_q = """
            MATCH (host:Host)
            MATCH host<-[r:Depends_on]-()
            WHERE not(host.operational_state = "Decommissioned") and r.public and (not(r.public_service) or not(has(r.public_service)))
            RETURN count(DISTINCT host) as public_host_count, count(r) as public_port_count
            """
        results = nc.query_to_dict(nc.neo4jdb, unauthorized_q)
        results.update(nc.query_to_dict(nc.neo4jdb, public_q))
        results['now'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
        results['domain'] = Site.objects.get_current().domain

        subject = 'NOCLook host security report'
        to = getattr(django_settings, 'SECURITY_REPORTS_TO', [])
        cc = getattr(django_settings, 'SECURITY_REPORTS_CC', None)
        bcc = getattr(django_settings, 'SECURITY_REPORTS_BCC', None)
        body = '''
            This is an auto generated host security report from NOCLook.

            Unauthorized ports:
            {unauthorized_host_count} hosts have unauthorized ports.
            There are a total of {unauthorized_port_count} unauthorized ports.

            See https://{domain}/reports/hosts/host-services/unauthorized-ports/ for more information.

            ---

            Public ports:
            {public_host_count} hosts have unverified public ports.
            There are a total of {public_port_count} unverified public ports.

            See https://{domain}/reports/hosts/host-services/public/ for more information.

            This report was generated on {now} UTC.
            '''.format(**results)

        msg = helpers.create_email(subject, body, to, cc, bcc)
        msg.send()

