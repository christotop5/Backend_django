"""
Django settings for VORA / OptimRoute CM backend.
"""

import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-dev-only-change-in-production',
)
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
TRAJECTORY_TOLERANCE_METERS = int(os.environ.get('TRAJECTORY_TOLERANCE_METERS', '500'))
SPRING_BOOT_RESERVATION_SERVICE_URL = os.environ.get('SPRING_BOOT_RESERVATION_SERVICE_URL', '')


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    return {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': parsed.path.lstrip('/'),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname,
        'PORT': parsed.port or 5432,
        'OPTIONS': {'sslmode': 'require'},
    }


DATABASE_URL = os.environ.get('DATABASE_URL', '')
if not DATABASE_URL:
    raise ValueError('DATABASE_URL environment variable is required.')

DATABASES = {'default': _database_from_url(DATABASE_URL)}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'accounts',
    'core',
    'payments',
    'geolocation',
    'optimization',
    'operations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'VORA Django Geo & Optimization API',
    'DESCRIPTION': 'Geolocation, zones, driver trajectories, turn optimization — OptimRoute CM',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'TAGS': [
        {'name': 'Geolocation', 'description': 'Google Maps wrapper endpoints'},
        {'name': 'Zones', 'description': 'Yaoundé taxi zones'},
        {'name': 'Carrefours', 'description': 'Pickup/drop reference points'},
        {'name': 'Driver Trajectories', 'description': 'Driver work corridors (turns)'},
        {'name': 'Optimization', 'description': 'Turn optimizer & corridor matching'},
        {'name': 'Admin', 'description': 'Dashboard aggregation endpoints'},
        {'name': 'System', 'description': 'Health checks'},
    ],
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if not DEBUG else []
