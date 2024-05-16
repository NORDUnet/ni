# -*- coding: utf-8 -*-

from os.path import abspath, basename, dirname, join, normpath
from os import environ
from sys import path
import dotenv

__author__ = 'lundberg'

"""
Common settings and globals.

Based on https://github.com/rdegges/django-skel/.
"""

########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Read .env for settings
config_file = environ.get('CONFIG_FILE', join(SITE_ROOT, '.env'))
dotenv.read_dotenv(config_file)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# SAML config
APP_SERVER_NAME =  environ.get("APP_SERVER_NAME", "norpan-ni.cnaas.sunet.se")
KEY_FILE =  environ.get("KEY_FILE", "/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/privkey.pem")
CERT_FILE =  environ.get("CERT_FILE", "/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/cert.pem")
SP_IDP =  environ.get("SP_IDP", None)
LOCAL_METADATA =  environ.get("LOCAL_METADATA", None)
MDQ_URL= environ.get("MDQ_URL", None)
MDQ_CERT= environ.get("MDQ_CERT", None)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION

########## PROJECT CONFIGURATION
try:
    from secrets import *
except ImportError:
    #NETAPP_REPORT_SETTINGS = [
    #    {
    #        'volumes': [re.compile('pattern')],
    #        'service_id': '',
    #        'contract_reference': '',
    #        'total_storage': 0.0
    #    }
    #]
    NETAPP_REPORT_SETTINGS = []
########## END PROJECT CONFIGURATION

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

########## END DEBUG CONFIGURATION

########## BRAND / HOME ORGANISATION
BRAND = environ.get('BRAND', 'NORDUnet')

LOGO_COLOR = environ.get('LOGO_COLOR', '')
LOGO_SUBTEXT = environ.get('LOGO_SUBTEXT', '')
LINK_COLOR = environ.get('LINK_COLOR', '')
LINK_HOVER = environ.get('LINK_HOVER', '')

########## END BRAND / HOME ORGANISATION

########## ALLOWED HOSTS CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = environ.get('ALLOWED_HOSTS', '').split()
########## END ALLOWED HOST CONFIGURATION

########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
########## END DATABASE CONFIGURATION


########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'Europe/Stockholm'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# Login settings
LOGIN_URL = environ.get('LOGIN_URL', '/login/')
AUTH_PROFILE_MODULE = 'userprofile.UserProfile'

DATETIME_FORMAT = "N j, Y, H:i"
TIME_FORMAT = "H:i"
########## END GENERAL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = environ.get('MEDIA_ROOT', normpath(join(DJANGO_ROOT, 'media')))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = environ.get('MEDIA_URL', '/media/')
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = environ.get('STATIC_ROOT', normpath(join(DJANGO_ROOT, 'static')))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = environ.get('STATIC_URL', '/static/')

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(DJANGO_ROOT, 'assets')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(DJANGO_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            normpath(join(DJANGO_ROOT, 'templates')),
        ],
        'APP_DIRS': True,
        'OPTIONS': { 
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'dynamic_preferences.processors.global_preferences',
                'apps.noclook.announcements.page_flash',
                'apps.noclook.context_processors.brand',
            ]
        }
    }
]


########## END TEMPLATE CONFIGURATION


### LOGIN conf
DJANGO_LOGIN_DISABLED = environ.get('DJANGO_LOGIN_DISABLED', 'False').lower() == 'false'
SAML_ENABLED = environ.get('SAML_ENABLED', 'False').lower() == 'false'

########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)
########## END MIDDLEWARE CONFIGURATION

########## AUTHENTICATION BACKENDS CONFIGURATION
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)
if SAML_ENABLED:
    AUTHENTICATION_BACKENDS += (
        environ.get('SAML_BACKEND', 'apps.saml2auth.middleware.ModifiedSaml2Backend'),
    )
    # environ.get('SAML_BACKEND', 'djangosaml2.backends.Saml2Backend'),
    MIDDLEWARE += (
        'djangosaml2.middleware.SamlSessionMiddleware',
        'apps.saml2auth.middleware.HandleUnsupportedBinding',
    )
    # Needed since django 2+ sets lax per default
    # SESSION_COOKIE_SAMESITE = None
    SESSION_COOKIE_SECURE = True
######### END AUTHENTICATION BACKENDS CONFIGURATION

########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION


########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Admin panel and documentation:
    'django.contrib.admin',
)

THIRD_PARTY_APPS = (
    'tastypie',
    'actstream',
    'django_comments',
    'crispy_forms',
    'dynamic_preferences',
    'attachments',
)

LOCAL_APPS = (
    'apps.userprofile',
    'apps.noclook',
    'apps.scan',
    'apps.nerds',
)

OPTIONAL_APPS = environ.get('OPTIONAL_APPS', '').split()

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

ACTSTREAM_SETTINGS = {
    'MANAGER': 'actstream.managers.ActionManager',
    'FETCH_RELATIONS': True,
    'USE_PREFETCH': True,
    'USE_JSONFIELD': True,
    'GFK_FETCH_DEPTH': 1,
}
########## END APP CONFIGURATION


########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
LOG_PATH = environ.get('LOG_PATH', '{!s}/logs'.format(SITE_ROOT))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'debugfile': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{!s}/django_debug.log'.format(LOG_PATH),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'errorfile': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{!s}/django_error.log'.format(LOG_PATH),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
        'error_console': {
            'level': 'ERROR',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        '': {
            'handlers': ['debugfile', 'errorfile', 'error_console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
########## END LOGGING CONFIGURATION

########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'wsgi.application'
########## END WSGI CONFIGURATION
