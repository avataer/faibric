"""
Django settings for faibric_backend project.
"""
import os
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent
_project_root = BASE_DIR.parent

# Load .env files - ALWAYS load both, .env.local overrides .env
# This ensures env vars survive Django's auto-reloader child processes
_env_main = _project_root / '.env'
_env_local = _project_root / '.env.local'

# Load base .env first
if _env_main.exists():
    load_dotenv(_env_main, override=False)

# Then load .env.local to override (for local development)
if _env_local.exists():
    load_dotenv(_env_local, override=True)

# CRITICAL: Also set in os.environ for child processes
# This fixes Django's StatReloader not inheriting load_dotenv vars
for env_file in [_env_main, _env_local]:
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Only set if not already in environment (preserves explicit overrides)
                    if key not in os.environ or env_file == _env_local:
                        os.environ[key] = value

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-this')

# SECURITY: DEBUG defaults to True for development safety
# In production, explicitly set DEBUG=0
DEBUG = os.getenv('DEBUG', '1') in ('1', 'true', 'True', 'TRUE', '')

# ALLOWED_HOSTS must be set BEFORE any potential early exit
# This prevents "You must set ALLOWED_HOSTS" errors
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', '.onrender.com', '.faibric.com']

# Frontend URL (for emails and CORS)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Email settings
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@faibric.com')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Local apps
    'apps.users',
    'apps.tenants',  # Multi-tenant security (must be before other apps)
    'apps.projects',
    'apps.ai_engine',
    'apps.templates',
    'apps.deployment',
    'apps.stocks',  # Real stock data API
    'apps.gateway',  # Universal API Gateway
    'apps.platform',  # Built-in platform services (DB, Auth, Storage)
    'apps.billing',  # Billing and payments
    'apps.analytics',  # Analytics and funnel tracking
    'apps.email_lists',  # Email subscriptions and newsletters
    'apps.chat',  # AI chat widget with multi-LLM support
    'apps.messaging',  # Unified messaging (email, SMS, push, in-app)
    'apps.forum',  # Community forum and discussions
    'apps.storage',  # File storage with S3/local support
    'apps.checkout',  # E-commerce checkout with Stripe/PayPal
    'apps.cabinet',  # Client cabinets (end-user dashboards)
    'apps.admin_builder',  # Drag & drop admin panel builder
    'apps.marketing',  # Marketing analysis and competitor tracking
    'apps.code_library',  # Code library and reuse system
    'apps.recommendations',  # Recommendation engine
    'apps.credits',  # Credits and usage tracking
    'apps.platform_admin',  # Faibric admin dashboard
    'apps.insights',  # Customer insights & quality assurance
    'apps.onboarding',  # Landing page & onboarding flow
]

# LLM API Keys (for platform-wide usage)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROK_API_KEY = os.getenv('GROK_API_KEY')

# Deployment settings (Render + GitHub)
RENDER_API_KEY = os.getenv('RENDER_API_KEY', '')
RENDER_OWNER_ID = os.getenv('RENDER_OWNER_ID', '')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_APPS_REPO = os.getenv('GITHUB_APPS_REPO', 'avataer/faibric-apps')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenants.middleware.TenantMiddleware',  # Multi-tenant isolation
    'apps.tenants.middleware.TenantAuditMiddleware',  # Security audit logging
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'faibric_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'faibric_backend.wsgi.application'

# Database configuration
import dj_database_url

USE_SQLITE = os.getenv('USE_SQLITE', '0') == '1'
DATABASE_URL = os.getenv('DATABASE_URL')

if USE_SQLITE:
    # SQLite for local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif DATABASE_URL:
    # Parse DATABASE_URL (for Render and other cloud providers)
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Fall back to individual environment variables
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'faibric_db'),
            'USER': os.getenv('DB_USER', 'faibric_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'faibric_password'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS Settings - Allow all origins for development
# Deployed apps run on subdomains like batman1-myapp-123.localhost
# They need to call http://localhost:8000/api/v1/db/...
CORS_ALLOW_ALL_ORIGINS = True  # Allow all for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-tenant-id",  # Multi-tenant header
]

# App subdomain base for deployments
APP_SUBDOMAIN_BASE = os.getenv('APP_SUBDOMAIN_BASE', 'localhost')

# Cache Configuration - MUST use Redis for shared cache between containers
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',  # Use DB 1 for cache (DB 0 for Celery)
    }
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# LLM Configuration
# Primary: Anthropic Claude Opus 4.5 for code generation
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Secondary: OpenAI for embeddings only
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# PayPal Configuration  
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET', '')

# Docker Configuration
DOCKER_HOST = os.getenv('DOCKER_HOST', 'unix://var/run/docker.sock')

# App Generation Settings
MAX_APPS_PER_USER = 10
APP_SUBDOMAIN_BASE = os.getenv('APP_SUBDOMAIN_BASE', 'localhost')

