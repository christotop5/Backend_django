"""
Django settings for VORA / OptimRoute CM backend.
"""

import os
import sys
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

_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
_default_hosts = 'localhost,127.0.0.1,.onrender.com'
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('ALLOWED_HOSTS', _default_hosts).split(',') if h.strip()
]
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
TRAJECTORY_TOLERANCE_METERS = int(os.environ.get('TRAJECTORY_TOLERANCE_METERS', '500'))
SPRING_BOOT_RESERVATION_SERVICE_URL = os.environ.get('SPRING_BOOT_RESERVATION_SERVICE_URL', '')

_INVALID_ENV_VALUES = {'true', 'false', 'none', 'null', ''}


def _parse_csv_env(name: str) -> list[str]:
    raw = os.environ.get(name, '')
    if raw.strip().lower() in _INVALID_ENV_VALUES:
        return []
    return [part.strip() for part in raw.split(',') if part.strip()]


def _valid_http_origins(values: list[str]) -> list[str]:
    """Keep only real http(s) origins — ignore booleans like 'True' from mis-set env vars."""
    origins = []
    for value in values:
        lowered = value.lower()
        if lowered in _INVALID_ENV_VALUES:
            continue
        if lowered.startswith(('http://', 'https://')):
            origins.append(value.rstrip('/'))
    return origins


def _database_from_url(url: str) -> dict:
    # Render internal URLs may use postgres:// — normalize for urlparse
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)

    parsed = urlparse(url)
    hostname = parsed.hostname or ''

    # Internal Render Postgres hostnames end with "-a" (no public domain)
    is_render_internal = hostname.endswith('-a') and '.render.com' not in hostname
    db_options = {'sslmode': 'prefer'} if is_render_internal else {'sslmode': 'require'}

    return {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': parsed.path.lstrip('/'),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': hostname,
        'PORT': parsed.port or 5432,
        'OPTIONS': db_options,
    }


DATABASE_URL = os.environ.get('DATABASE_URL', '')
_collectstatic = 'collectstatic' in sys.argv

if DATABASE_URL:
    DATABASES = {'default': _database_from_url(DATABASE_URL)}
elif _collectstatic:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / '.collectstatic-build.sqlite3',
        }
    }
else:
    raise ValueError('DATABASE_URL environment variable is required.')

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

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

_cors_origins = _valid_http_origins(_parse_csv_env('CORS_ALLOWED_ORIGINS'))
if _render_host:
    _render_origin = f'https://{_render_host}'
    if _render_origin not in _cors_origins:
        _cors_origins.append(_render_origin)

CORS_ALLOW_ALL_ORIGINS = DEBUG and not _cors_origins
CORS_ALLOWED_ORIGINS = _cors_origins

# Production security (Render terminates TLS at the edge)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

_csrf_origins = _valid_http_origins(_parse_csv_env('CSRF_TRUSTED_ORIGINS'))
if _render_host:
    _render_origin = f'https://{_render_host}'
    if _render_origin not in _csrf_origins:
        _csrf_origins.append(_render_origin)
CSRF_TRUSTED_ORIGINS = _csrf_origins

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
}
