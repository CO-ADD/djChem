"""
Django settings for adjCHEM project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from pathlib import Path
from datetime import timedelta
import psycopg2.extensions

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
VERSION = '0.1'
DEBUG = True

print(f"Project: adjCHEM ")
print(f"BaseDir: {BASE_DIR}")
print(f"Version: {VERSION}")
print(f"Debug: {DEBUG}")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-#$34$_)0$79ey2s(yn0-)o+8(xp^r*eu$6%8t17lgpno7610f-'


ALLOWED_HOSTS = ["0.0.0.0", "imb-coadd.imb.uq.edu.au", "localhost", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',


    'django.contrib.humanize',   
    "django.contrib.postgres",
    'django_rdkit',
    'django_filters',
    "sequences.apps.SequencesConfig",
    'apputil.apps.AppUtilConfig',
    'dcoadd.apps.dCOADDConfig',

    #'rest_framework',
    #'rest_framework.authtoken',
    'formtools',
    'pgtrigger',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'adjCHEM.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'adjCHEM.wsgi.application'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = 'static/'
STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR.parent, 'static')

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases
#--------------------------------------------------------------------
DB_NAME = os.environ.get('db_name') or 'chemdb'
DB_USER = os.environ.get('db_usr') or 'chemdb'
DB_PASSWD = os.environ.get('password') or 'chemdb'
PG_ENGINE = 'django.db.backends.postgresql_psycopg2'
HOST_NAME = 'imb-coadd-db.imb.uq.edu.au'

print(f"Database Name: {DB_NAME}@{HOST_NAME} ")

DATABASES = {
    'default': {
        "ENGINE": PG_ENGINE,
        'OPTIONS':{'options': '-c search_path=djutil,public', 
                   'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,},
        'NAME': DB_NAME,'USER': DB_USER, 'PASSWORD':DB_PASSWD,
        'HOST': HOST_NAME, 'PORT': '5432',
    },

    'dcoadd': {
        "ENGINE": PG_ENGINE,
        'OPTIONS':{'options': '-c search_path=coadd,djutil,public', 
                   'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,},
        'NAME': DB_NAME,'USER': DB_USER, 'PASSWORD':DB_PASSWD,
        'HOST': HOST_NAME, 'PORT': '5432',
    },
}

DATABASE_ROUTERS = ['adjCHEM.routers.DatabaseRouter',]

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators
AUTH_USER_MODEL = 'apputil.ApplicationUser'

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/
#--------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Brisbane'
USE_I18N = True
USE_TZ = True
DATE_FORMAT = "d-m-Y"
USE_L10N = False

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

LOGOUT_REDIRECT_URL="/"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# RDKit Settings
#--------------------------------------------------------------------
DJANGO_RDKIT_MOL_SERIALIZATION = "TEXT"

# Logging
#--------------------------------------------------------------------
LOGGING = {
    "version": 1,  # the dictConfig format version
    "disable_existing_loggers": False,  # retain the default loggers
    "level": "INFO",

}