#!/usr/bin/env python
import os
import sys
import dotenv
from django.core.exceptions import ImproperlyConfigured

if __name__ == "__main__":
    dotenv.read_dotenv()
    from django.core.management import execute_from_command_line
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'niweb.settings')

    try:
        execute_from_command_line(sys.argv)
    except ImproperlyConfigured as e:
        print(e)
        print('Maybe you forgot to use manage.py [command] --settings=niweb.settings.dev|prod')
