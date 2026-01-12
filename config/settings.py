import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (환경 변수 사용을 위해)
load_dotenv()

# 프로젝트 내부 경로를 빌드합니다: BASE_DIR / 'subdir'와 같이 사용
BASE_DIR = Path(__file__).resolve().parent.parent


# 빠른 시작 개발 설정 - 프로덕션에는 부적합
# 자세한 내용은 https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/ 참조

# 보안 경고: 프로덕션에서 사용되는 SECRET_KEY는 반드시 비밀로 유지하세요!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-secret-key-for-dev')

# 보안 경고: 프로덕션에서는 DEBUG 모드를 켜지 마세요!
DEBUG = os.getenv('DEBUG', '1') == '1'

# .env의 DJANGO_ALLOWED_HOSTS를 파싱, 각 호스트의 공백을 제거하여 안정성을 높임
ALLOWED_HOSTS = [host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')]


# 애플리케이션 정의

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework', # Django REST Framework
    'django_celery_results', # Celery 작업 결과를 DB에 저장하기 위해 추가
    # Local apps
    'music', # 우리가 만든 'music' 앱 추가
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# 데이터베이스 설정
# 자세한 내용은 https://docs.djangoproject.com/en/4.2/ref/settings/#databases 참조

DATABASES = {
    'default': {
        'ENGINE': os.getenv('SQL_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('SQL_DATABASE', 'music_db'),
        'USER': os.getenv('SQL_USER', 'music_user'),
        'PASSWORD': os.getenv('SQL_PASSWORD', 'music_password'),
        'HOST': os.getenv('SQL_HOST', 'db'), # docker-compose 서비스 이름
        'PORT': os.getenv('SQL_PORT', '5432'), # PostgreSQL 기본 포트
    }
}


# 비밀번호 유효성 검사
# 자세한 내용은 https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators 참조
# 기본 Django 비밀번호 유효성 검사기
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

# 커스텀 사용자 모델
# AUTH_USER_MODEL = 'music.User' # 우리가 만든 User 모델을 사용하도록 설정 (TODO: music 앱 생성 필요)

# 국제화 설정
# 자세한 내용은 https://docs.djangoproject.com/en/4.2/topics/i18n/ 참조

LANGUAGE_CODE = 'ko-kr' # 한국어 설정

TIME_ZONE = 'Asia/Seoul' # 서울 시간대 설정

USE_I18N = True

USE_TZ = True


# 정적 파일 (CSS, JavaScript, 이미지)
# 자세한 내용은 https://docs.djangoproject.com/en/4.2/howto/static-files/ 참조

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static_root' # collectstatic 명령 시 정적 파일이 모이는 경로

# 미디어 파일 (사용자가 업로드한 파일)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media_root' # 사용자가 업로드한 파일이 저장되는 경로

# 기본 기본 키 필드 타입
# 자세한 내용은 https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field 참조

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery 설정
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')
CELERY_RESULT_BACKEND = 'django-db' # Celery 작업 결과를 Django DB에 저장 (django-celery-results 사용)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_ENABLE_UTC = False