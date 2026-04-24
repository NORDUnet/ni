import os
import sys
## Need to change this path depending on where the Django project is
## located.
base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'niweb')
sys.path.append(os.path.abspath(base_path))
niweb_path = os.path.join(base_path, 'niweb')
sys.path.append(os.path.abspath(niweb_path))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "niweb.settings.prod")
import django
from django.conf import settings as django_settings
#django cache hack
django_settings.CACHES['default']['LOCATION'] = '/tmp/django_cache_consumer'
django.setup()


def nop():
    pass
