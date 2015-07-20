#!/usr/bin/env python
import os
import sys
from django.core.exceptions import ImproperlyConfigured

if __name__ == "__main__":

    from django.core.management import execute_from_command_line
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'niweb.settings')

    try:
        execute_from_command_line(sys.argv)
    except ImproperlyConfigured:
        print 'Use manage.py [command] --settings=niweb.settings.dev|prod'
