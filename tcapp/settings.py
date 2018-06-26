# Copyright (c) 2018, TeaCapp LLC
#   All rights reserved.

import logging, os.path, sys

from django.contrib.messages import constants as messages
from django.core.urlresolvers import reverse_lazy

from deployutils.configs import load_config, update_settings

#pylint: disable=undefined-variable

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = os.path.basename(APP_ROOT)
BASE_DIR = APP_ROOT

SLUG_RE = '[a-zA-Z0-9-]+'

update_settings(sys.modules[__name__],
    load_config(APP_NAME, 'credentials', 'site.conf', verbose=True,
        location=os.getenv("SETTINGS_LOCATION", None),
        passphrase=os.getenv("SETTINGS_CRYPT_KEY", None)))

if os.getenv('DEBUG'):
    # Enable override on command line.
    DEBUG = True if int(os.getenv('DEBUG')) > 0 else False

DATABASES = {
    'default': {
        'ENGINE':DB_ENGINE,
        'NAME': DB_NAME,
        'USER': DB_USER,                 # Not used with sqlite3.
        'PASSWORD': DB_PASSWORD,         # Not used with sqlite3.
        'HOST': DB_HOST,                 # Not used with sqlite3.
        'PORT': DB_PORT,                 # Not used with sqlite3.
        'TEST_NAME': ':memory:',
    }
}

# Installed apps
# --------------
if DEBUG:
    ENV_INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.admindocs',
        'debug_toolbar',
        'django_extensions',
        )
else:
    ENV_INSTALLED_APPS = tuple([])

INSTALLED_APPS = ENV_INSTALLED_APPS + (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'deployutils.apps.django',
    'crispy_forms',
    'rest_framework',
    'django_assets',
    'pages',
    'tcapp'
)

# Process requests pipeline
# -------------------------
# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tcapp.wsgi.application'

if DEBUG:
    MIDDLEWARE_CLASSES = (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
        )
else:
    MIDDLEWARE_CLASSES = ()

MIDDLEWARE_CLASSES += (
    'django.middleware.common.CommonMiddleware',
    'deployutils.apps.django.middleware.RequestLoggingMiddleware',
    'deployutils.apps.django.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'tcapp.urls'

MANAGERS = ADMINS

EMAIL_SUBJECT_PREFIX = '[%s] ' % APP_NAME
EMAILER_BACKEND = 'extended_templates.backends.TemplateEmailBackend'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOG_HANDLER = {
    'level': 'DEBUG',
    'formatter': 'request_format' if DEBUG else 'json',
    'filters': ['request'],
    'class':'logging.StreamHandler',
}
if logging.getLogger('gunicorn.error').handlers:
    #pylint:disable=invalid-name
    _handler = logging.getLogger('gunicorn.error').handlers[0]
    if isinstance(_handler, logging.FileHandler):
        LOG_HANDLER.update({
            'class':'logging.handlers.WatchedFileHandler',
            'filename': LOG_FILE
        })
    else:
        # stderr or logging.handlers.SysLogHandler
        LOG_HANDLER.update({'class': "%s.%s" % (
            _handler.__class__.__module__, _handler.__class__.__name__)})

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        # Add an unbound RequestFilter.
        'request': {
            '()': 'deployutils.apps.django.logging.RequestFilter',
        },
    },
    'formatters': {
        'simple': {
            'format': 'X X %(levelname)s [%(asctime)s] %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z'
        },
        'json': {
            '()': 'deployutils.apps.django.logging.JSONFormatter',
            'format':
            'gunicorn.' + APP_NAME + '.app: [%(process)d] '\
                '%(log_level)s %(remote_addr)s %(http_host)s %(username)s'\
                ' [%(asctime)s] %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z',
            'replace': False,
            'whitelists': {
                'record': [
                    'nb_queries', 'queries_duration',
                    'charge', 'amount', 'unit', 'modified',
                    'customer', 'organization', 'provider'],
            }
        },
        'request_format': {
            'format':
            '%(levelname)s %(remote_addr)s %(username)s [%(asctime)s]'\
                ' %(message)s "%(http_user_agent)s"',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z'
        }
    },
    'handlers': {
        'db_log': {
            'level': 'DEBUG',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
            'class':'logging.StreamHandler',
        },
        'log': LOG_HANDLER,
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    'loggers': {
        'boto': {
            # AWSAuthConnection.get_object() will log 2 errors and raise
            # an exception. That's a little too much.
            'handlers': ['log'],
            'level': 'ERROR',
            'propagate': False
        },
        'deployutils': {
            'handlers': ['db_log'],
            'level': 'INFO',
            'propagate': False
        },
        'tcapp': {
            'handlers': [],
            'level': 'DEBUG',
        },
#        'django.db.backends': {
#           'handlers': ['db_log'],
#           'level': 'DEBUG',
#           'propagate': False
#        },
        'django.request': {
            'handlers': [],
            'level': 'ERROR',
        },
        # If we don't disable 'django' handlers here, we will get an extra
        # copy on stderr.
        'django': {
            'handlers': [],
        },
        'requests': {
            'handlers': [],
            'level': 'WARNING',
        },
        # This is the root logger.
        # The level will only be taken into account if the record is not
        # propagated from a child logger.
        #https://docs.python.org/2/library/logging.html#logging.Logger.propagate
        '': {
            'handlers': ['log', 'mail_admins'],
            'level': 'INFO'
        },
    },
}

# API settings
# ------------
REST_FRAMEWORK = {
    'PAGE_SIZE': 25,
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    )
}
if not DEBUG:
    REST_FRAMEWORK.update({
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    })

# Language settings
# -----------------

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
#
# We must use UTC here otherwise the date of request in gunicorn access
# and error logs will be off compared to the dates shown in nginx logs.
# (see https://github.com/benoitc/gunicorn/issues/963)
TIME_ZONE = 'UTC'


# Static assets
# -------------

ASSETS_DEBUG = DEBUG
ASSETS_AUTO_BUILD = DEBUG
ASSETS_ROOT = APP_ROOT + '/htdocs/static'

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
if not hasattr(sys.modules[__name__], 'MEDIA_ROOT'):
    MEDIA_ROOT = APP_ROOT + '/htdocs/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/tcapp/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
HTDOCS = APP_ROOT + '/htdocs'
APP_STATIC_ROOT = HTDOCS + '/static'
if DEBUG:
    STATIC_ROOT = ''
    # Additional locations of static files
    STATICFILES_DIRS = (APP_STATIC_ROOT,)
    STATIC_URL = '/%s/static/' % APP_NAME
else:
    STATIC_ROOT = APP_STATIC_ROOT
    STATIC_URL = '/static/'

ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django_assets.finders.AssetsFinder'
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Template settings
# -----------------
THEMES_DIRS = (
    os.path.join(BASE_DIR, 'themes'),
)

# There is no bootstrap class for ".alert-error".
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

CRISPY_TEMPLATE_PACK = 'bootstrap3'
CRISPY_CLASS_CONVERTERS = {'textinput':"form-control"}

# List of callables that know how to import templates from various sources.
TEMPLATES_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATES_DIRS = (
    os.path.join(APP_ROOT, 'tcapp', 'templates'),
)

TEMPLATES_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
)

# Django 1.8+
TEMPLATES = [
    {
        'BACKEND': 'extended_templates.backends.eml.EmlEngine',
        'DIRS': TEMPLATES_DIRS,
    },
    {
        'BACKEND': 'extended_templates.backends.pdf.PdfEngine',
        'DIRS': TEMPLATES_DIRS,
        'OPTIONS': {
            'loaders': TEMPLATES_LOADERS
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATES_DIRS,
        'OPTIONS': {
            'context_processors': [proc.replace(
                'django.core.context_processors',
                'django.template.context_processors')
                for proc in TEMPLATES_CONTEXT_PROCESSORS],
            'loaders': TEMPLATES_LOADERS,
            'libraries': {},
            'builtins': [
                'django_assets.templatetags.assets',
                'deployutils.apps.django.templatetags.deployutils_prefixtags',
                'deployutils.apps.django.templatetags.deployutils_extratags',
                'tcapp.templatetags.tcapptags'
            ]
        }
    }
]


# User settings
# -------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = reverse_lazy('application_base')

# The Django Middleware expects to find the authentication backend
# before returning an authenticated user model.
AUTHENTICATION_BACKENDS = (
    'deployutils.apps.django.backends.auth.ProxyUserBackend',)

# debug_toolbar settings
# ----------------------
DEBUG_TOOLBAR_PATCH_SETTINGS = False
DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': '%svendor/jquery.js' % STATIC_URL,
    'SHOW_COLLAPSED': True,
}
INTERNAL_IPS = ('127.0.0.1', '::1')  # Yes, this one is also for debug_toolbar.

# Session settings
# ----------------
# The default session serializer switched to JSONSerializer in Django 1.6
# but just to be sure:
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = 'deployutils.apps.django.backends.encrypted_cookies'

DEPLOYUTILS = {
    # Hardcoded mockups here.
    'MOCKUP_SESSIONS': {
        'donny': {
            'username': 'donny',
            'roles': {'manager': [
                {'slug': 'tcapp', 'full_name': 'TeaCapp'},
                {'slug': 'nextgen-tower', 'full_name': 'NextGen Tower',
                 'subscriptions': [{
                     'plan': 'verification',
                     'ends_at': '2018-12-31T00:00:00+00:00'}]}]},
            'site': {'email': 'donny@djaodjin.com'}},
        'alice': {
            'username': 'alice',
            'roles': {'manager': [
                {'slug': 'nextgen-tower', 'full_name': 'NextGen Tower',
                 'subscriptions': [{
                     'plan': 'verification',
                     'ends_at': '2018-12-31T00:00:00+00:00'}]}]},
            'site': {'email': 'alice@djaodjin.com'}},
    },
    'ALLOWED_NO_SESSION': [
        STATIC_URL,
        reverse_lazy('login'),
        reverse_lazy('snaplines_page')]
}
