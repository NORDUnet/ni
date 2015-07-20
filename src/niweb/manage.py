#!/usr/bin/env python
import os
import sys
import django

if __name__ == "__main__":

    from django.core.management import execute_from_command_line

    try:
        execute_from_command_line(sys.argv)
    except django.core.exceptions.ImproperlyConfigured:
        print 'Use manage.py [command] --settings=app.noclook.settings.dev|prod'
