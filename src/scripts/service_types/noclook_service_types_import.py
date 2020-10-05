import os
import sys
import argparse
import csv
import logging

base_path = '../../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'niweb.settings.prod')
import django
django.setup()
from apps.noclook.models import ServiceType, ServiceClass

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

    with open(args.csv_file, 'r') as csv_file:
        rows = csv.reader(csv_file)
        #skip header
        if not args.no_header:
             next(rows, None)
        for name, service_class in rows:
            insert_service_type(name, service_class)

if __name__ == '__main__':
    main()
