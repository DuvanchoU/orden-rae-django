"""
Django settings for orden_rae project.
"""
import os
from pathlib import Path
from decouple import config
from dotenv import load_dotenv

# ==========================================
# CARGA DE VARIABLES DE ENTORNO (.env)
# ==========================================
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================
# SEGURIDAD
# ==========================================
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-cambia-esto-en-produccion')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
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
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Producción: servir estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'usuarios.middleware.NoCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # ← Requerido por OAuth
    'ventas.middleware.ClientesAuthMiddleware',  # Clientes primero
    'usuarios.middleware.CustomAuthMiddleware',   # Staff después
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
                'django.template.context_processors.request',  # ← Requerido por allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pagos.context_processors.stripe_settings',
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
    'default': dj_database_url.config(
        default=os.getenv(
            'DATABASE_URL',
            'postgresql://postgres@localhost:5432/bd_orden_rae_django'
        ),
        conn_max_age=600,
        ssl_require=not DEBUG
    )
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
# ALLAUTH - OAUTH 2.0 (Configuración Actualizada)
# ==========================================
# Configuración de login
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_UNIQUE_EMAIL = True

# Configuración de signup (nueva sintaxis)
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']

# Configuración social
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = False

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'CLIENT_ID': os.getenv('SOCIALACCOUNT_PROVIDERS_GOOGLE_CLIENT_ID'),
        'SECRET': os.getenv('SOCIALACCOUNT_PROVIDERS_GOOGLE_SECRET'),
    }
}

SOCIALACCOUNT_ADAPTER = 'pagina.adapters.CustomSocialAccountAdapter'

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
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost,http://127.0.0.1').split(',')

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
# STRIPE
# ==========================================
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', 'pk_test_51TYVv0CGUP1IqyPzfEb75sDRQnUvbvbIDI9l7YoQv7Wd4xjziycCWgBBwCPeAvRycDLdedk8D1SmKMdXRhh6IXR800PUiOUGls')
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default='')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

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

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    api_key=os.getenv('CLOUDINARY_API_KEY', ''),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', ''),
    secure=True
)

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET', ''),
    'FOLDER': 'orden-rae',
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Wompi Configuration
WOMPI_PUBLIC_KEY = os.getenv('WOMPI_PUBLIC_KEY', '')
WOMPI_PRIVATE_KEY = os.getenv('WOMPI_PRIVATE_KEY', '')
WOMPI_INTEGRITY_SECRET = os.getenv('WOMPI_INTEGRITY_SECRET', '')
WOMPI_BASE_URL = os.getenv('WOMPI_BASE_URL', 'https://api.wompi.co/v1')
WOMPI_CHECKOUT_URL = os.getenv('WOMPI_CHECKOUT_URL', 'https://checkout.wompi.co')