"""
Django settings for scheduler project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PRODUCTION = False

# Generate file with
# openssl rand -base64 100
if PRODUCTION:
  with open('/etc/django_secret_key.txt') as f:
    SECRET_KEY = f.read().strip()
else:
  with open('/etc/django_secret_key_testing.txt') as f:
    SECRET_KEY = f.read().strip()

DEBUG = not PRODUCTION

TEMPLATE_DEBUG = not PRODUCTION

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'solver',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'scheduler.urls'

WSGI_APPLICATION = 'scheduler.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

if PRODUCTION:
  DJANGO_LOG_FILE = '/var/log/django/production.log'
else:
  DJANGO_LOG_FILE = '/var/log/django/debug.log'
LOGGING = {
 'version': 1,
 'disable_existing_loggers': False,
 'handlers': {
   'file': {
     'level': 'DEBUG',
     'class': 'logging.FileHandler',
     'filename': DJANGO_LOG_FILE,
   },
 },
 'loggers': {
   'django.request': {
     'handlers': ['file'],
     'level': 'DEBUG',
     'propagate': True,
   },
 },
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'

STATIC_ROOT = '/var/www/static/'
