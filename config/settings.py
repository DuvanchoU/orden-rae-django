import os
from pathlib import Path
from decouple import config
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured 

# ==========================================
# CARGA DE VARIABLES DE ENTORNO (.env)
# ==========================================
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# Helper para variables OBLIGATORIAS
# Si falta una variable crítica, la app NO arranca.
# ==========================================
def env_required(name: str) -> str:
    """Obtiene una variable de entorno. Lanza error si falta o está vacía."""
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(
            f"❌ La variable de entorno '{name}' es obligatoria y no está definida. "
            f"Revisa tu archivo .env o las variables de entorno del servidor."
        )
    return value


def env_optional(name: str, default: str = '') -> str:
    """Obtiene una variable opcional con valor por defecto seguro."""
    return os.getenv(name, default)


# ==========================================
# SEGURIDAD
# ==========================================
SECRET_KEY = env_required('SECRET_KEY')

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ==========================================
# APLICACIONES
# ==========================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # OAuth 2.0 / Social Login
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Nuestras Apps
    'dashboard',
    'usuarios',
    'inventario',
    'ventas',
    'compras',
    'produccion',
    'pagina',
    'reports',
    'pagos',
    'cloudinary',
    'cloudinary_storage',
]

# ==========================================
# MIDDLEWARE (Combinado: OAuth + Producción)
# ==========================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'usuarios.middleware.NoCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'ventas.middleware.ClientesAuthMiddleware',
    'usuarios.middleware.CustomAuthMiddleware',
    'usuarios.middleware.SessionIdleTimeoutMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ==========================================
# URLs y Templates
# ==========================================
ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pagos.context_processors.wompi_settings',
                'ventas.context_processors.carrito_context',
                'usuarios.context_processors.user_permissions',
                'django.template.context_processors.media',
                'ventas.context_processors.cliente_auth_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ==========================================
# BASE DE DATOS (PostgreSQL Render)
# ==========================================
import dj_database_url

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'bd_orden_rae_django'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': env_required('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5433'),
        'OPTIONS': {
            'client_encoding': 'UTF8',
        },
    }
}

# ==========================================
# VALIDACIÓN DE CONTRASEÑAS
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==========================================
# INTERNACIONALIZACIÓN
# ==========================================
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ==========================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ==========================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ==========================================
# AUTENTICACIÓN (CONFIGURACIÓN UNIFICADA)
# ==========================================
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'usuarios.backends.UsuariosAuthBackend',
    'ventas.backends.ClientesAuthBackend',
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ==========================================
# ALLAUTH - OAUTH 2.0
# ==========================================
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = False

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APPS': [
            {
                'client_id': os.getenv('SOCIALACCOUNT_PROVIDERS_GOOGLE_CLIENT_ID'),
                'secret': os.getenv('SOCIALACCOUNT_PROVIDERS_GOOGLE_SECRET'),
                'key': '',
            },
        ],
    }
}

# Conservamos solo el adapter de 'usuarios' que era el que ganaba.
SOCIALACCOUNT_ADAPTER = "usuarios.social_adapter.MySocialAccountAdapter"

# ==========================================
# SESIONES
# ==========================================
SESSION_COOKIE_AGE = 86400
ADMIN_SESSION_TIMEOUT = 300
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SAMESITE = 'Lax'

# ==========================================
# SEGURIDAD
# ==========================================
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CSRF_COOKIE_SECURE = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost,http://127.0.0.1'
).split(',')

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ==========================================
# EMAIL
# ==========================================
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

if 'smtp' in EMAIL_BACKEND.lower():
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@ordenrae.com')

PASSWORD_RESET_TIMEOUT = 3600
EMAIL_VERIFICATION_TIMEOUT = 86400
SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000')

# ==========================================
# LÍMITES DE ARCHIVOS
# ==========================================
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', 10485760))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', 10485760))

# ==========================================
# MENSAJES
# ==========================================
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ==========================================
# CACHÉ
# ==========================================
# NOTA: LocMemCache NO funciona bien con múltiples workers de Gunicorn.
# Si activas rate-limiting real en producción, migra a Redis.
# Por ahora lo dejamos así para desarrollo.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ==========================================
# LOGGING
# ==========================================
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'security.log'),
            'formatter': 'verbose',
        },
        'django_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'django_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

# ==========================================
# MISCELÁNEO
# ==========================================
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================
# CONFIGURACIÓN PARA RENDER (PRODUCCIÓN)
# ==========================================
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# ==========================================
# CLOUDINARY - Almacenamiento de Imágenes
# ==========================================
import cloudinary
import cloudinary.uploader
import cloudinary.api

CLOUDINARY_CLOUD_NAME = env_required('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = env_required('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = env_required('CLOUDINARY_API_SECRET')

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
    'FOLDER': 'orden-rae',
}

# ==========================================
# STORAGES (Static + Media)
# ==========================================
import sys

# Detectar si estamos corriendo tests
TESTING = 'test' in sys.argv or 'pytest' in sys.modules

if TESTING:
    # En tests: usar storage simple que NO requiere collectstatic
    _staticfiles_backend = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    # En producción/desarrollo: usar WhiteNoise con manifiesto
    _staticfiles_backend = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": _staticfiles_backend,
    },
}

# ==========================================
# WOMPI - Configuración de Pagos
# ==========================================
WOMPI_PUBLIC_KEY = os.environ.get('WOMPI_PUBLIC_KEY')
WOMPI_PRIVATE_KEY = os.environ.get('WOMPI_PRIVATE_KEY')
WOMPI_INTEGRITY_SECRET = os.environ.get('WOMPI_INTEGRITY_SECRET')
WOMPI_EVENTS_SECRET = os.environ.get('WOMPI_EVENTS_SECRET')
WOMPI_CURRENCY = os.environ.get('WOMPI_CURRENCY', 'COP')
WOMPI_BASE_URL = os.environ.get('WOMPI_BASE_URL', '')