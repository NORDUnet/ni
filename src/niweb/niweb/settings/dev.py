# -*- coding: utf-8 -*-

from os import environ
import json
from .common import *

__author__ = 'lundberg'

"""Development settings and globals."""

########## PROJECT CONFIGURATION
# Neo4j settings
NEO4J_RESOURCE_URI = environ.get('NEO4J_RESOURCE_URI', 'bolt://localhost:7687')
NEO4J_MAX_DATA_AGE = environ.get('NEO4J_MAX_DATA_AGE', '24')  # hours
NEO4J_USERNAME = environ.get('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = environ.get('NEO4J_PASSWORD', 'docker')

TEST_NEO4J_URI = environ.get('TEST_NEO4J_URI', '')
TEST_NEO4J_USERNAME = environ.get('TEST_NEO4J_USERNAME', 'neo4j')
TEST_NEO4J_PASSWORD = environ.get('TEST_NEO4J_PASSWORD', 'docker')

# To be able to use the report mailing functionality you need to set a to address and a key.
REPORTS_TO = environ.get('REPORTS_TO', '').split()
REPORTS_CC = environ.get('REPORTS_CC', '').split()     # Optional
REPORTS_BCC = environ.get('REPORTS_BCC', '').split()   # Optional
# EXTRA_REPORT_TO = {'ID': ['address', ]}
EXTRA_REPORT_TO = json.loads(environ.get('EXTRA_REPORT_TO', '{}'))  # Optional
SECURITY_REPORTS_TO = environ.get('SECURITY_REPORTS_TO', '').split()
SECURITY_REPORTS_CC = environ.get('SECURITY_REPORTS_CC', '').split()     # Optional
SECURITY_REPORTS_BCC = environ.get('SECURITY_REPORTS_BCC', '').split()   # Optional
########## END PROJECT CONFIGURATION

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

########## END DEBUG CONFIGURATION

SESSION_COOKIE_DOMAIN = '.localni.info'
LOGIN_REDICRECT_URL = 'http://react.localni.info'

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': environ.get('DB_ENGINE', 'django.db.backends.postgresql_psycopg2'),
        'NAME': environ.get('DB_NAME', 'norduni'),
        'USER': environ.get('DB_USER', 'ni'),
        'PASSWORD': environ.get('DB_PASSWORD', 'docker'),
        'HOST': environ.get('DB_HOST', 'localhost'),
        'PORT': environ.get('DB_PORT', '5432')
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION

########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INSTALLED_APPS += (
    'debug_toolbar',
    'django_nose',
    'django_extensions'
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
) + MIDDLEWARE_CLASSES

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': lambda x: False,
}
########## END TOOLBAR CONFIGURATION

########## SECRET CONFIGURATION
SECRET_KEY = environ.get('SECRET_KEY', 'development')
########## END SECRET CONFIGURATION

########## TESTING
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
########## END TESTING

GOOGLE_MAPS_API_KEY = environ.get('GOOGLE_MAPS_API_KEY', 'no-apikey')
CORS_ORIGIN_ALLOW_ALL = True
