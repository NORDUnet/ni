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

# URL of the login page.
LOGIN_URL = '/login/'

# django-debug-toolbar settings
INTERNAL_IPS = ('127.0.0.1',)
DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)

# Django settings, change these if needed.
SERVER_EMAIL = 'django@example.com'
ADMINS = (
    ('Admin', 'webmaster@example.com'),
)
MANAGERS = ADMINS

# To get an e-mail when someone comments, please fill in a
# mail server.
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
NEO4J_RESOURCE_URI = "http://localhost:9999/"

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
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
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
    'apps.noclook',
    'debug_toolbar',
)
