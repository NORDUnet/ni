import os
import sys
import argparse
import csv
import logging

from norduni.scripts import django_setup

django_setup.nop()

from norduni.apps.noclook.models import ServiceType, ServiceClass

logger = logging.getLogger('noclook_service_types_import')

def insert_service_type(name, service_class):
    try:
        service_class_, created = ServiceClass.objects.get_or_create(name=service_class)
        service_type, created = ServiceType.objects.get_or_create(name=name, service_class=service_class_)
    except Exception:
        logger.warning('Bad things happened importing {} - {}'.format(name, service_class))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file', help='The csv file to import')
    parser.add_argument('--no_header', action='store_true', default=False, help='CSV file has no header')
    args = parser.parse_args()

    with open(args.csv_file, 'rb') as csv_file:
        rows = csv.reader(csv_file)
        #skip header
        if not args.no_header:
            rows.next()
        for name, service_class in rows:
            insert_service_type(name, service_class)

if __name__ == '__main__':
    main()
