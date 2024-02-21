# -*- coding: utf-8 -*-

from os import environ
import json
from apps.saml2auth import config
from .common import *

__author__ = 'lundberg'

"""Production settings and globals."""

########## PROJECT CONFIGURATION
# Neo4j settings
NEO4J_RESOURCE_URI = environ.get('NEO4J_RESOURCE_URI', 'bolt://localhost:7687')
NEO4J_MAX_DATA_AGE = environ.get('NEO4J_MAX_DATA_AGE', '24')  # hours
NEO4J_USERNAME = environ.get('NEO4J_USERNAME')
NEO4J_PASSWORD = environ.get('NEO4J_PASSWORD')
# To be able to use the report mailing functionality you need to set a to address and a key.
REPORTS_TO = environ['REPORTS_TO'].split()
REPORTS_CC = environ.get('REPORTS_CC', '').split()     # Optional
REPORTS_BCC = environ.get('REPORTS_BCC', '').split()   # Optional
# EXTRA_REPORT_TO = {'ID': ['address', ]}
EXTRA_REPORT_TO = json.loads(environ.get('EXTRA_REPORT_TO', '{}'))
SECURITY_REPORTS_TO = environ['SECURITY_REPORTS_TO'].split()
SECURITY_REPORTS_CC = environ.get('SECURITY_REPORTS_CC', '').split()     # Optional
SECURITY_REPORTS_BCC = environ.get('SECURITY_REPORTS_BCC', '').split()   # Optional
########## PROJECT CONFIGURATION

########## END GENERAL CONFIGURATION
# djangosaml2 settings
ENABLE_DISCOVERY_SERVICE = environ.get('ENABLE_DISCOVERY_SERVICE', 'False').lower() != 'false'
# DISCOVERY_SERVICE_URL = environ.get('DISCOVERY_SERVICE_URL', 'https://service.seamlessaccess.org/ds')
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SAML_CREATE_UNKNOWN_USER = True

SAML_USE_NAME_ID_AS_USERNAME = True
SAML_DJANGO_USER_MAIN_ATTRIBUTE = 'username'
SAML_DJANGO_USER_MAIN_ATTRIBUTE_LOOKUP = '__iexact'

SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SAML2_DISCO_URL = 'https://ds.qa.swamid.se/ds'
if ENABLE_DISCOVERY_SERVICE:
    SAML2_DISCO_URL = environ.get('DISCOVERY_SERVICE_URL', 'https://service.seamlessaccess.org/ds')

APPEND_SLASH = False
LOGIN_URL = '/saml2/login/'
LOGOUT_URL = '/logout/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SAML_ATTRIBUTE_MAPPING = {
    'eduPersonPrincipalName': ('username', ),
    'email': ('email', ),
    'givenName': ('first_name', ),
    'sn': ('last_name', ),
    'displayName': ('display_name', ),
    'eduPersonEntitlement': ('eduPersonEntitlement', ),
}



SAML_CONFIG = config.CONFIG
########## END GENERAL CONFIGURATION

########## SENTRY CONFIGURATION
# Set your DSN value
RAVEN_CONFIG = {
    'dsn': environ.get('SENTRY_DSN', ''),
}
########## END SENTRY CONFIGURATION

########## APP CONFIGURATION
INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django.raven_compat',
    'djangosaml2',
)
########## APP CONFIGURATION

########## EMAIL CONFIGURATION
DEFAULT_FROM_EMAIL = environ['DEFAULT_FROM_EMAIL']
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = environ.get('EMAIL_HOST', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = environ.get('EMAIL_PORT', '')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % SITE_NAME

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = EMAIL_HOST_USER
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
DATABASES = {
    'default': {
        'ENGINE': environ.get('DB_ENGINE', 'django.db.backends.postgresql_psycopg2'),
        'NAME': environ.get('DB_NAME', 'norduni'),
        'USER': environ.get('DB_USER', 'ni'),
        'PASSWORD': environ['DB_PASSWORD'],
        'HOST': environ.get('DB_HOST', 'localhost'),
        'PORT': environ.get('DB_PORT', '5432')
    }
}
########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': environ.get('CACHE_BACKEND', 'django.core.cache.backends.filebased.FileBasedCache'),
        'LOCATION': environ.get('CACHE_LOCATION', '/tmp/django_cache'),
    }
}

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 3600  # 1h
CACHE_MIDDLEWARE_KEY_PREFIX = ''
########## END CACHE CONFIGURATION

########## SECRET CONFIGURATION
SECRET_KEY = environ['SECRET_KEY']
########## END SECRET CONFIGURATION

GOOGLE_MAPS_API_KEY = environ.get('GOOGLE_MAPS_API_KEY', 'no-apikey')
