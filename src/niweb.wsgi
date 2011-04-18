mport os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'niweb.settings'

sys.path.append('/path/to/niweb')
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
