from os import environ
from os.path import join
from sys import path

# Django settings for niweb project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
STATIC_DEV_MEDIA = path_to_static_media_for_development

NIWEB_ROOT = ''
# URL without the host name,
# eg. /niweb/ for http://www.example.com/niweb/.
NIWEB_URL = '/'
# URL without the host name,
# eg. /niweb/media/ for http://www.example.com/niweb/media/.
NIWEB_MEDIA_URL = '/site_media/'

# Add niweb directory to the python path
path.append(NIWEB_ROOT)

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = join(NIWEB_ROOT, 'static/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = NIWEB_MEDIA_URL

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = join(NIWEB_URL, 'static/admin/')

# Django mail settings, change these if needed.
SERVER_EMAIL = 'django@example.com'
ADMINS = (
    ('Admin', 'webmaster@example.com'),
)
MANAGERS = ADMINS

# Please fill in a mail server.
DEFAULT_FROM_EMAIL = 'postmaster@example.com'
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = '25'

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': join(NIWEB_ROOT, 'niweb.sqlite3'),
    }
}

# Neo4j settings
NEO4J_RESOURCE_URI = '/path/to/neo4jdb/'
environ['NEO4J_PYTHON_JVMARGS'] = '-Xms128M -Xmx512M'
NEO4J_MAX_DATA_AGE = '24' # hours

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Stockholm'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-US'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
)

ROOT_URLCONF = 'niweb.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    join(NIWEB_ROOT, 'templates/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.flatpages',
    'django.contrib.comments',
    'django.contrib.markup',
    'niweb_core',
    'apps.fedlogin',
    'apps.noclook',
)
