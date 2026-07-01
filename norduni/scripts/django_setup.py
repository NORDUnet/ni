"""
This module is used to set up Django when running scripts from the command line. It should be imported before importing any models or other Django code.
The nop function can be called to prevent IDEs from complaining about unused imports.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "norduni.niweb.settings.prod")

django.setup()


def nop():
    pass
