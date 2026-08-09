"""Configuration Django de Tier Fist.

Tous les secrets proviennent de variables d'environnement (spec §51, §66).
La base de données est PostgreSQL en développement comme en production (spec §3.4) :
SQLite n'est jamais utilisé, y compris pour les tests.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent

env = environ.Env()
# Le .env est à la racine du dépôt afin d'être partagé entre backend et outillage.
for candidate in (REPO_DIR / ".env", BASE_DIR / ".env"):
    if candidate.exists():
        env.read_env(str(candidate))
        break

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
# La sonde de santé Railway interroge le conteneur avec cet en-tête Host :
# sans cette entrée, elle recevrait un 400 DisallowedHost et le déploiement
# échouerait alors que l'application est saine.
ALLOWED_HOSTS.append("healthcheck.railway.app")
# Railway fournit le domaine public via cette variable.
RAILWAY_PUBLIC_DOMAIN = env("RAILWAY_PUBLIC_DOMAIN", default="")
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "accounts",
    "tierlists",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# Le build Vite est copié ici lors du déploiement : Django sert le SPA.
FRONTEND_DIST_DIR = REPO_DIR / "frontend" / "dist"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIST_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# En développement, l'absence de DATABASE_DB retombe sur le PostgreSQL de
# docker-compose. En production, ce repli serait un piège : le conteneur
# tenterait de joindre 127.0.0.1 et échouerait avec une pile d'appels illisible.
# On préfère refuser de démarrer avec un message explicite.
DEV_DATABASE_DB = "postgres://tierfist:tierfist@localhost:5433/tierfist"
if not DEBUG and not env("DATABASE_DB", default=""):
    raise ImproperlyConfigured(
        "DATABASE_DB n'est pas définie alors que DJANGO_DEBUG=False.\n"
        "Sur Railway : ouvre le service web -> onglet Variables -> New Variable "
        "-> Add Reference -> choisis le service Postgres puis DATABASE_DB.\n"
        "La variable doit apparaître sous la forme ${{Postgres.DATABASE_DB}}."
    )

DATABASES = {"default": env.db_url("DATABASE_DB", default=DEV_DATABASE_DB)}
DATABASES["default"].setdefault("CONN_MAX_AGE", 60)

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Le build Vite est construit avec base=/static/ : ses fichiers sont collectés
# tels quels et servis par WhiteNoise.
STATICFILES_DIRS = [FRONTEND_DIST_DIR] if FRONTEND_DIST_DIR.exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Compression sans manifeste : Vite hache déjà les noms de fichiers, et le
    # post-traitement du manifeste casserait les références internes du bundle.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Uploads ---------------------------------------------------------------
# Limite technique (anti-DoS), volontairement configurable et non présentée
# comme une règle métier (spec §14.2).
MAX_UPLOAD_IMAGE_SIZE = env.int("MAX_UPLOAD_IMAGE_SIZE", default=5 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_IMAGE_SIZE + 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_IMAGE_SIZE

# --- DRF -------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "config.exceptions.tierfist_exception_handler",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

# --- Sécurité / cookies (spec §6.2, §51) -----------------------------------
SESSION_COOKIE_NAME = "tierfist_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

CSRF_COOKIE_NAME = "tierfist_csrftoken"
# Le SPA doit pouvoir lire ce cookie pour renvoyer l'en-tête X-CSRFToken :
# il n'est donc pas HttpOnly. Le cookie de session, lui, l'est.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    # La sonde de santé arrive en HTTP depuis le réseau interne : la rediriger
    # vers HTTPS ferait échouer tous les déploiements.
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# En développement, Vite tourne sur un autre port : on autorise les credentials
# cross-origin. En production tout est servi par la même origine.
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"] if DEBUG else [],
)

# --- Logs (spec §63) -------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        # Journal métier : transitions de statut, finalisation, ranking, jokers.
        "tierfist": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
