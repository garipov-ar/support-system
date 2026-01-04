from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-secret")
DEBUG = os.getenv("DEBUG") == "1"

ALLOWED_HOSTS = ["*"]

# --- APPS ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "django_ckeditor_5",
    "mptt",
    
    "apps.users",
    "apps.content.apps.ContentConfig",
    "apps.bot",
    'apps.analytics',
]

# --- MIDDLEWARE (КРИТИЧНО ДЛЯ ADMIN) ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- URLS ---
ROOT_URLCONF = "config.urls"

# --- TEMPLATES (КРИТИЧНО ДЛЯ ADMIN) ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# --- WSGI ---
WSGI_APPLICATION = "config.wsgi.application"

# --- DATABASE ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
    }
}

# --- AUTH ---
AUTH_USER_MODEL = "users.User"

# --- PASSWORDS ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Yekaterinburg"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('ru', 'Russian'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# --- STATIC / MEDIA ---
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# CKEditor 5
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link', 'bulletedList', 'numberedList', 'blockQuote', 'undo', 'redo'],
    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': ['heading', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
        'subscript', 'superscript', 'highlight', '|', 'code', 'codeBlock', '|', 'bulletedList', 'numberedList', 'todoList',
        '|',  'outdent', 'indent', '|', 'blockQuote', 'insertImage', '|',
        'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'mediaEmbed', 'removeFormat',
        'insertTable',],
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                'imageStyle:alignCenter', 'imageStyle:alignRight'],
            'styles': [
                'alignLeft',
                'alignCenter',
                'alignRight',
            ]
        },
        'table': {
            'contentToolbar': ['tableColumn', 'tableRow', 'mergeTableCells',
            'tableProperties', 'tableCellProperties'],
            'tableProperties': {
                'borderColors': '...',
                'backgroundColors': '...'
            },
            'tableCellProperties': {
                'borderColors': '...',
                'backgroundColors': '...'
            }
        },
        'heading' : {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        }
    },
    'list': {
        'properties': {
            'styles': 'true',
            'startIndex': 'true',
            'reversed': 'true',
        }
    }
}
CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage" # or any other storage

STATIC_ROOT = BASE_DIR / "static"

# --- DEFAULT PK ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- TELEGRAM ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# --- CELERY ---
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/1')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
