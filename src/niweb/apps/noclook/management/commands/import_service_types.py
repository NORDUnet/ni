# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import argparse
import os
import sys
import csv
import logging

from apps.noclook.models import ServiceType, ServiceClass
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger('noclook_service_types_import')


def insert_service_type(name, service_class):
    try:
        service_class_, created = ServiceClass.objects\
                                    .get_or_create(name=service_class)
        service_type, created = ServiceType.objects\
                                    .get_or_create(name=name,
                                        service_class=service_class_)
    except Exception:
        logger.warning('Bad things happened importing {} - {}'\
            .format(name, service_class))


class Command(BaseCommand):
    help = 'Import service types'

    def add_arguments(self, parser):
        parser.add_argument('--csv_file', help='The csv file to import',
                            type=argparse.FileType('r'))
        parser.add_argument('--no_header', action='store_true',
            default=False, help='CSV file has no header')


    def handle(self, *args, **options):
        with open(options['csv_file'], 'r') as csv_file:
            rows = csv.reader(csv_file)

            #skip header
            if not options['no_header']:
                next(rows, None)

            for name, service_class in rows:
                insert_service_type(name, service_class)
