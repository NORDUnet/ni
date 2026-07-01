import os
import sys
import argparse
import csv
import logging
import django

base_path = '../../niweb/'
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'niweb.settings.prod')

django.setup()
from apps.noclook.models import Dropdown, Choice

logger = logging.getLogger('noclook_dropdown_import')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file', help='The csv file to import')
    args = parser.parse_args()

    with open(args.csv_file, 'rb') as csv_file:
        for row in csv.DictReader(csv_file):
            dropdown, created = Dropdown.objects.get_or_create(name=row['dropdown'])
            value = row['value']
            name = row['name'] or value
            if value:
                Choice.objects.get_or_create(dropdown=dropdown,
                                             value=value,
                                             name=name)


if __name__ == '__main__':
    main()
