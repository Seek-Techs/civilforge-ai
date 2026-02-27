"""
Django settings for civilforge project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# SECURITY
# Never put real secrets directly in this file.
# They live in your .env file which is never committed to Git.
# ------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-me-before-deploying'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*'] if DEBUG else os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')


# ------------------------------------------------------------------
# INSTALLED APPS
# Think of this as Django's "plugin list".
# Order matters — django.contrib.sites must come before allauth.
# ------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Required by allauth
    'django.contrib.sites',

    # allauth core + providers
    'allauth',
    'allauth.account',          # email/password registration
    'allauth.socialaccount',    # Google, GitHub etc (we'll add later)

    # Our app
    'projects',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # allauth needs this to handle account actions
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'civilforge.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # global templates folder
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

WSGI_APPLICATION = 'civilforge.wsgi.application'


# ------------------------------------------------------------------
# DATABASE
# SQLite for now — simple file, great for learning.
# We'll switch to PostgreSQL in Stage 8 (deployment).
# ------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ------------------------------------------------------------------
# PASSWORD VALIDATION
# These are rules Django enforces when a user sets a password.
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ------------------------------------------------------------------
# ALLAUTH CONFIGURATION
# This is the heart of Stage 1. Every setting is explained below.
# ------------------------------------------------------------------

# allauth needs a "site ID" to support multi-site setups.
# We only have one site, so this is always 1.
SITE_ID = 1

# Tell Django to use allauth's authentication backend
# (so allauth can log users in after email confirmation, etc.)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',       # default Django auth
    'allauth.account.auth_backends.AuthenticationBackend',  # allauth
]

# --- allauth behaviour settings ---

# Users sign in with their email address, not username
ACCOUNT_LOGIN_METHODS = {'email'}

# Email address is required to register
ACCOUNT_EMAIL_REQUIRED = True

ACCOUNT_USERNAME_REQUIRED = False 
# Users must verify their email before they can log in
# Change to 'optional' during development if you don't want to set up email yet
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

# After login, go to the projects dashboard
LOGIN_REDIRECT_URL = '/my-projects/'

# After logout, go to the login page
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'

# Log out immediately without asking "are you sure?"
ACCOUNT_LOGOUT_ON_GET = True

# Minimum password length
ACCOUNT_PASSWORD_MIN_LENGTH = 8

# Rate-limit login attempts to prevent brute force attacks
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5         # max failed attempts
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300     # lock out for 5 minutes


# ------------------------------------------------------------------
# EMAIL
# In development: emails print to the terminal (no real email sent).
# In production: swap to a real SMTP service like Brevo.
# ------------------------------------------------------------------
if DEBUG:
    # This "backend" just prints emails to your terminal.
    # When you register, look at the terminal to get the confirmation link.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp-relay.brevo.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@civilforge.ai')


# ------------------------------------------------------------------
# INTERNATIONALISATION
# ------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ------------------------------------------------------------------
# OLLAMA / LLM (from environment, with sensible defaults)
# ------------------------------------------------------------------
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')


# ------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'projects': {'handlers': ['console'], 'level': 'DEBUG' if DEBUG else 'INFO'},
        'django.server': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
