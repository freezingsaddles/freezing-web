"""
Django settings for bafs project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '0(h6n^m7jvs@o&ntz98i%ppx6b^^z=*gj*8&m8=k-%u*^ku!z_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'bafs',
    'rest_framework'
)

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ]
}

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'bafs.urls'

WSGI_APPLICATION = 'bafs.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.mysql',
        'NAME': 'bafs',
        'USER': 'freezing',
        'PASSWORD': 'itscold'
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

# APP-SPECIFIC

# The strava team (club) IDs
BAFS_TEAMS = [
              46292, # Team 0
              46380, # Team 1
              46386, # Team 2
              46418, # Team 3
              46225, # Team 4
              46334, # Team 5
              46402, # Team 6
              46246, # Team 7
              46209, # Team 8
              46202, # Team 9
              ]

# When does the competition start?
BAFS_START_DATE = '2014-01-01'

# When does the competition end?  (This can be an exact time; API will stop fetching after this time.)
BAFS_END_DATE = '2014-03-20 00:01:00-04:00'

# How many days after end of competition to upload rides?
BAFS_UPLOAD_GRACE_PERIOD_DAYS = 5

# Keywords to exclude from ride titles
BAFS_EXCLUDE_KEYWORDS = ['#NoBAFS']