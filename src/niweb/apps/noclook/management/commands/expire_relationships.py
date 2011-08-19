# -*- coding: utf-8 -*-
"""
Created on Fri Aug 19 11:28:13 2011

@author: lundberg
"""

from django.core.management.base import BaseCommand, CommandError
import datetime
import norduni_client as nc

class Command(BaseCommand):
    args = '<hours>'
    help = 'Deletes auto managed nodes that are older than <hours>.'

    def handle(self, *args, **options):
        try:
            hours = int(args[0])
        except Exception as e:
            raise CommandError(e)
        max_age = datetime.timedelta(hours=hours)
        now = datetime.datetime.now()
        for rel in nc.get_all_relationships():
            if rel.get('noclook_auto_manage', False):
                last_seen = datetime.datetime.strptime(rel['noclook_last_seen'], 
                                                       '%Y-%m-%dT%H:%M:%S.%f')
                if (now-last_seen) > max_age:
                    rel.delete()