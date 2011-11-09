mport os
import sys

sys.path.append('/path/to/niweb')
os.environ['DJANGO_SETTINGS_MODULE'] = 'niweb.settings'
java_home = os.getenv("JAVA_HOME")
if not java_home:
    os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-6-openjdk/jre"

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
