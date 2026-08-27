"""
Django settings for config project.
"""

from pathlib import Path
from datetime import timedelta
import os

from dotenv import load_dotenv


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-development-key-change-in-production",
)

DEBUG = (
    os.environ.get(
        "DJANGO_DEBUG",
        "True",
    ).lower()
    == "true"
)


# ============================================================
# ALLOWED HOSTS
# ============================================================

env_hosts = os.environ.get("ALLOWED_HOSTS", "")
if env_hosts:
    ALLOWED_HOSTS = [h.strip() for h in env_hosts.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = [
        "*",
        "localhost",
        "127.0.0.1",
    ]

# Render / Railway hostnames
render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",

    # Local
    "api",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND":
            "django.template.backends.django.DjangoTemplates",

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [

                "django.template.context_processors.request",

                "django.contrib.auth.context_processors.auth",

                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# WSGI / ASGI
# ============================================================

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE":
            "django.db.backends.sqlite3",

        "NAME":
            BASE_DIR / "db.sqlite3",
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        "NAME":
            (
                "django.contrib.auth.password_validation."
                "UserAttributeSimilarityValidator"
            ),
    },

    {
        "NAME":
            (
                "django.contrib.auth.password_validation."
                "MinimumLengthValidator"
            ),
    },

    {
        "NAME":
            (
                "django.contrib.auth.password_validation."
                "CommonPasswordValidator"
            ),
    },

    {
        "NAME":
            (
                "django.contrib.auth.password_validation."
                "NumericPasswordValidator"
            ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# MEDIA FILES
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {

    # --------------------------------------------------------
    # AUTHENTICATION
    # --------------------------------------------------------

    "DEFAULT_AUTHENTICATION_CLASSES": [

        "rest_framework_simplejwt.authentication.JWTAuthentication",

        # Required for DRF browsable API login.
        "rest_framework.authentication.SessionAuthentication",
    ],

    # --------------------------------------------------------
    # DEFAULT PERMISSION
    # --------------------------------------------------------

    "DEFAULT_PERMISSION_CLASSES": [

        "rest_framework.permissions.IsAuthenticated",
    ],

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    "DEFAULT_PAGINATION_CLASS":
        "api.pagination.StandardPagination",

    "PAGE_SIZE": 20,

    # --------------------------------------------------------
    # RENDERERS
    # --------------------------------------------------------

    "DEFAULT_RENDERER_CLASSES": [

        "rest_framework.renderers.JSONRenderer",

        "rest_framework.renderers.BrowsableAPIRenderer",
    ],

    # --------------------------------------------------------
    # PARSERS
    # --------------------------------------------------------

    "DEFAULT_PARSER_CLASSES": [

        "rest_framework.parsers.JSONParser",

        "rest_framework.parsers.MultiPartParser",

        "rest_framework.parsers.FormParser",
    ],

    # --------------------------------------------------------
    # OPENAPI
    # --------------------------------------------------------

    "DEFAULT_SCHEMA_CLASS":
        "drf_spectacular.openapi.AutoSchema",

    # --------------------------------------------------------
    # CUSTOM EXCEPTION HANDLER
    # --------------------------------------------------------

    "EXCEPTION_HANDLER":
        "api.exceptions.custom_exception_handler",
}


# ============================================================
# JWT CONFIGURATION
# ============================================================

SIMPLE_JWT = {

    # --------------------------------------------------------
    # ACCESS TOKEN
    # --------------------------------------------------------

    "ACCESS_TOKEN_LIFETIME":
        timedelta(hours=24),

    # --------------------------------------------------------
    # REFRESH TOKEN
    # --------------------------------------------------------

    "REFRESH_TOKEN_LIFETIME":
        timedelta(days=30),

    # --------------------------------------------------------
    # REFRESH TOKEN ROTATION
    # --------------------------------------------------------

    "ROTATE_REFRESH_TOKENS": False,

    "BLACKLIST_AFTER_ROTATION": False,

    # --------------------------------------------------------
    # AUTHORIZATION HEADER
    # --------------------------------------------------------

    "AUTH_HEADER_TYPES": (
        "Bearer",
    ),

    # --------------------------------------------------------
    # USER IDENTIFICATION
    # --------------------------------------------------------

    "USER_ID_FIELD": "id",

    "USER_ID_CLAIM": "user_id",

    # --------------------------------------------------------
    # TOKEN ALGORITHM
    # --------------------------------------------------------

    "ALGORITHM": "HS256",

    "SIGNING_KEY": SECRET_KEY,
}


# ============================================================
# SPECTACULAR / SWAGGER
# ============================================================

SPECTACULAR_SETTINGS = {

    "TITLE": "Full Stack API",

    "DESCRIPTION": (
        "Complete REST API for managing "
        "authentication, clients, quotes, "
        "invoices, payments, receipts, "
        "settings and reports."
    ),

    "VERSION": "1.0.0",

    "SERVE_INCLUDE_SCHEMA": False,

    # --------------------------------------------------------
    # SWAGGER UI
    # --------------------------------------------------------

    "SWAGGER_UI_SETTINGS": {

        "deepLinking": True,

        "persistAuthorization": True,

        "displayRequestDuration": True,

        "filter": True,
    },

    "SORT_OPERATIONS": False,

    "COMPONENT_SPLIT_REQUEST": True,

    # --------------------------------------------------------
    # JWT BEARER AUTHENTICATION
    # --------------------------------------------------------

    "SECURITY": [
        {
            "BearerAuth": []
        }
    ],

    "APPEND_COMPONENTS": {

        "securitySchemes": {

            "BearerAuth": {

                "type": "http",

                "scheme": "bearer",

                "bearerFormat": "JWT",

                "description": (
                    "Enter your JWT access token. "
                    "Example: Bearer eyJhbGciOiJIUzI1Ni..."
                ),
            }
        }
    },
}


# ============================================================
# RAZORPAY PAYMENT GATEWAY
# ============================================================
#
# IMPORTANT:
# Keep this Razorpay configuration ONLY ONCE.
#
# The actual values must come from:
# .env locally
# OR
# Render Environment Variables in production.
#
# NEVER put the secret key in React/Vite frontend code.
# ============================================================

RAZORPAY_KEY_ID = os.environ.get(
    "RAZORPAY_KEY_ID",
    "",
).strip()

RAZORPAY_KEY_SECRET = os.environ.get(
    "RAZORPAY_KEY_SECRET",
    "",
).strip()

RAZORPAY_WEBHOOK_SECRET = os.environ.get(
    "RAZORPAY_WEBHOOK_SECRET",
    "",
).strip()


# ============================================================
# CORS CONFIGURATION
# ============================================================

CORS_ALLOWED_ORIGINS = [

    # --------------------------------------------------------
    # VITE LOCALHOST
    # --------------------------------------------------------

    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",

    # --------------------------------------------------------
    # OTHER LOCAL FRONTEND SERVERS
    # --------------------------------------------------------

    "http://localhost:3000",
    "http://localhost:8080",

    # --------------------------------------------------------
    # 127.0.0.1
    # --------------------------------------------------------

    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",

    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]

# Allow all origins for seamless cloud deployment (Render, Vercel, Railway, etc.)
CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
    r"^https://.*\.onrender\.com$",
    r"^https://.*\.railway\.app$",
]

# ------------------------------------------------------------
# VERCEL FRONTEND
# ------------------------------------------------------------

vercel_frontend_url = os.environ.get("FRONTEND_URL")
if vercel_frontend_url:
    CORS_ALLOWED_ORIGINS.append(vercel_frontend_url.rstrip("/"))

CORS_ALLOW_CREDENTIALS = True


# ============================================================
# CORS API REGEX
# ============================================================

CORS_URLS_REGEX = r"^.*$"


# ============================================================
# CORS HEADERS
# ============================================================

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
]


# ============================================================
# CORS METHODS
# ============================================================

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]


# ============================================================
# CSRF TRUSTED ORIGINS
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "https://*.vercel.app",
    "https://*.onrender.com",
    "https://*.railway.app",
]

if vercel_frontend_url:
    CSRF_TRUSTED_ORIGINS.append(vercel_frontend_url.rstrip("/"))


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = os.environ.get(
    "EMAIL_HOST",
    "smtp.gmail.com",
)

EMAIL_PORT = int(
    os.environ.get(
        "EMAIL_PORT",
        "587",
    )
)

EMAIL_USE_TLS = (
    os.environ.get(
        "EMAIL_USE_TLS",
        "True",
    ).lower()
    == "true"
)

EMAIL_HOST_USER = os.environ.get(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_HOST_PASSWORD",
    "",
)

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER,
)


# ============================================================
# RAZORPAY CONFIGURATION
# ============================================================

RAZORPAY_KEY_ID = os.environ.get(
    "RAZORPAY_KEY_ID",
    "",
)

RAZORPAY_KEY_SECRET = os.environ.get(
    "RAZORPAY_KEY_SECRET",
    "",
)

RAZORPAY_WEBHOOK_SECRET = os.environ.get(
    "RAZORPAY_WEBHOOK_SECRET",
    "",
)


# ============================================================
# GOOGLE OAUTH CONFIGURATION
# ============================================================

GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "",
)


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)