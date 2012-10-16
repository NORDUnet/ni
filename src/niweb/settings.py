from os import environ
from os.path import join
from sys import path
from apps.saml2auth import config

SESSION_COOKIE_DOMAIN = 'ni.nordu.net'

# Django settings for niweb project.
DEBUG = False
TEMPLATE_DEBUG = DEBUG

NIWEB_ROOT = '/var/opt/norduni/src/niweb/'
# URL without the host name,
# eg. /niweb/ for http://www.example.com/niweb/.
NIWEB_URL = '/'

# Add niweb directory to the python path
path.append(NIWEB_ROOT)

# Static files collection
STATIC_ROOT = join(NIWEB_ROOT, 'sitestatic/')

# Static URL
STATIC_URL = '/static/'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = join(NIWEB_ROOT, 'media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL of the login page.
LOGIN_URL = '/saml2/login/'
AUTH_PROFILE_MODULE = 'userprofile.UserProfile'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SAML_CREATE_UNKNOWN_USER = True

SAML_ATTRIBUTE_MAPPING = {
    'eduPersonPrincipalName': ('username', ),
    'mail': ('email', ),
    'givenName': ('first_name', ),
    'sn': ('last_name', ),
    'displayName': ('display_name', ),
}

SAML_CONFIG = config.SAML_CONFIG

# Django settings, change these if needed.
SERVER_EMAIL = 'niweb@nordu.net'
ADMINS = (
    ('Johan Lundberg', 'lundberg@nordu.net'),
)
MANAGERS = ADMINS

# To get an e-mail when someone comments, please fill in a
# mail server.
DEFAULT_FROM_EMAIL = 'niweb@nordu.net'
EMAIL_HOST = 'localhost'
EMAIL_PORT = '25'

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'norduni2',
        'USER': 'postgres',
        'PASSWORD': 'ZAtRMffa-utxcO7',
        'HOST': 'localhost'
    }
}

# Neo4j settings
NEO4J_RESOURCE_URI = '/var/opt/norduni/dependencies/neo4jdb/'
environ['JAVA_HOME'] = '/usr/lib/jvm/java-6-openjdk/jre/' 
environ['NEO4J_PYTHON_JVMARGS'] = '-Xms1G -Xmx2G'
NEO4J_MAX_DATA_AGE = '24' # hours
# Properties that should be indexed in the search node or relationship index.
SEARCH_INDEX_KEYS = ['name', 'description', 'ip_address', 'ip_addresses',
                     'as_number', 'hostname', 'telenor_tn1_number']
# Other indexes used
OTHER_INDEXES = ['node_types']

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
SECRET_KEY = '2834y0iylylftiuk8708y7970YHN9ylil0U23yilyi48HTNtw4tt2G4EQFrgwrN83Y5HEG4URIS'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'djangosaml2.backends.Saml2Backend',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.static',
)

ROOT_URLCONF = 'niweb.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    join(NIWEB_ROOT, 'templates/'),
)

STATICFILES_DIRS = (
    join(NIWEB_ROOT, 'static/'),
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
    'django.contrib.staticfiles',
    'tastypie',
    'djangosaml2',
    'niweb_core',
    'apps.userprofile',
    'apps.noclook',
)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        }
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/ni/django_error.log',
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        }
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
    } 
}

