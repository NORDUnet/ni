import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "norduni.niweb.settings.prod")

django.setup()


def nop():
    pass
