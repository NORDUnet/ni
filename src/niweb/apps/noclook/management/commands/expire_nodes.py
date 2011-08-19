# -*- coding: utf-8 -*-
"""
Created on Fri Aug 19 11:28:13 2011

@author: lundberg
"""

from django.core.management.base import BaseCommand, CommandError
from apps.noclook.models import NodeHandle
import datetime
import norduni_client as nc

class Command(BaseCommand):
    args = '<hours>'
    help = 'Deletes auto managed nodes that are older than <hours> hours.'

    def handle(self, *args, **options):
        try:
            hours = int(args[0])
        except Exception as e:
            raise CommandError(e)
        max_age = datetime.timedelta(hours=hours)
        now = datetime.datetime.now()
        for n in nc.get_all_nodes():
            if n.get('noclook_auto_manage', False):
                last_seen = datetime.datetime.strptime(n['noclook_last_seen'], 
                                                       '%Y-%m-%dT%H:%M:%S.%f')
                if (now-last_seen) > max_age:
                    NodeHandle.objects.get(pk=n.handle_id).delete()
                    #nc.delete_node(n.id)