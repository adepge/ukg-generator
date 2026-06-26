from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

# Load the environment variables.
load_dotenv(REPO_ROOT / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "this-is-my-secret-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "kg",
]

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

CORS_ALLOW_ALL_ORIGINS = True

# The directory containing the pipeline modules (extraction_module.py and generate_triples.py)
UKG_SRC_DIR = REPO_ROOT / "src"

# -----------------------------------------------------------------------------
# LLM-as-judge triple evaluation (src/evaluation.py)
# -----------------------------------------------------------------------------
# When enabled, generated triples are scored by the LLM judge during ingestion
# and only triples whose mean normalized score (0-1, averaged across the
# correctness/relevance/well-formedness dimensions) is >= UKG_JUDGE_MIN_SCORE
# are persisted. Requires OPENAI_API_KEY (see .env.example); when the key is
# missing the step is skipped and all triples are kept (fail-open).
UKG_JUDGE_EVALUATION_ENABLED = os.environ.get("UKG_JUDGE_EVALUATION_ENABLED", "1") == "1"

try:
    UKG_JUDGE_MIN_SCORE = float(os.environ.get("UKG_JUDGE_MIN_SCORE", "0.5"))
except ValueError:
    UKG_JUDGE_MIN_SCORE = 0.5

# Directory where per-document LLM-as-judge reports are written as JSON.
UKG_EVAL_REPORT_DIR = Path(
    os.environ.get("UKG_EVAL_REPORT_DIR", MEDIA_ROOT / "evaluations")
)

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Display logging level for the UKG application (evaluation step)
UKG_LOG_LEVEL = os.environ.get("UKG_LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        # Application loggers (kg.services, kg.tasks, ...).
        "kg": {
            "handlers": ["console"],
            "level": UKG_LOG_LEVEL,
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
