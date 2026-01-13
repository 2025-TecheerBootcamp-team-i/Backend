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

# 개발 환경에서는 모든 호스트 허용
if DEBUG:
    ALLOWED_HOSTS = ['*']


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
    'rest_framework_simplejwt', # JWT 인증 (Access/Refresh 토큰)
    'corsheaders', # CORS 설정 (프론트엔드와 통신)
    'drf_spectacular', # Swagger/OpenAPI 문서 자동 생성
    'django_celery_results', # Celery 작업 결과를 DB에 저장하기 위해 추가
    # Local apps
    'music', # 우리가 만든 'music' 앱 추가
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS 미들웨어 (최상단 근처에 위치)
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

# ==============================================
# Django REST Framework 설정
# ==============================================
# REST API의 기본 인증 및 권한 설정을 정의합니다.
REST_FRAMEWORK = {
    # 기본 인증 방식: JWT(JSON Web Token)를 사용합니다.
    # 클라이언트는 로그인 후 발급받은 토큰을 Authorization 헤더에 포함하여 요청합니다.
    # 예: Authorization: Bearer <access_token>
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    
    # 기본 권한 정책: 모든 사용자에게 접근 허용 (인증 불필요)
    # 개별 View에서 permission_classes를 지정하여 인증을 요구할 수 있습니다.
    # 예: permission_classes = [IsAuthenticated]
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    
    # Swagger/OpenAPI 스키마 생성 (API 문서 자동화)
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

from datetime import timedelta

# ==============================================
# JWT(JSON Web Token) 상세 설정
# ==============================================
# 사용자 인증에 사용되는 JWT 토큰의 동작 방식을 정의합니다.
SIMPLE_JWT = {
    # Access Token 유효 기간: 24시간 (시연/개발용으로 길게 설정)
    # 프로덕션 환경에서는 15분~1시간 권장
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    
    # Refresh Token 유효 기간: 30일
    # Access Token이 만료되면 Refresh Token으로 새로운 Access Token을 발급받습니다.
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    
    # Refresh Token 갱신 시 새로운 Refresh Token도 함께 발급
    # 보안 강화: 이전 Refresh Token은 무효화됩니다.
    'ROTATE_REFRESH_TOKENS': True,
    
    # 토큰 암호화 알고리즘: HMAC SHA-256
    'ALGORITHM': 'HS256',
    
    # 토큰 서명에 사용할 비밀 키 (Django SECRET_KEY 사용)
    'SIGNING_KEY': SECRET_KEY,
    
    # Authorization 헤더의 타입: "Bearer <token>" 형식 사용
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ==============================================
# CORS (Cross-Origin Resource Sharing) 설정
# ==============================================
# 프론트엔드(React)와 백엔드(Django)가 다른 도메인에서 실행될 때
# 브라우저의 보안 정책(Same-Origin Policy)을 우회하여 통신을 허용합니다.
#
# 예시:
# - 프론트엔드: http://localhost:3000 (React 개발 서버)
# - 백엔드: http://localhost:8000 (Django API 서버)
# → CORS 설정 없이는 브라우저가 요청을 차단합니다.

if DEBUG:
    # 개발 환경: 모든 Origin(도메인)에서의 요청을 허용
    # 주의: 프로덕션에서는 절대 사용하지 마세요! (보안 위험)
    CORS_ALLOW_ALL_ORIGINS = True
else:
    # 프로덕션 환경: 허용할 도메인을 명시적으로 지정 (화이트리스트 방식)
    CORS_ALLOWED_ORIGINS = [
        'https://your-frontend-domain.vercel.app',  # Vercel 배포 도메인 (실제 도메인으로 변경 필요)
        'http://localhost:3000',  # React 개발 서버 (로컬 테스트용)
        'http://localhost:5173',  # Vite 개발 서버 (로컬 테스트용)
    ]

# CORS 쿠키 및 인증 정보 전송 허용
# True로 설정 시 프론트엔드에서 쿠키, Authorization 헤더 등을 포함한 요청 가능
# JWT 토큰을 사용하므로 Authorization 헤더 전송이 필요합니다.
CORS_ALLOW_CREDENTIALS = True

# CORS 요청 시 허용할 HTTP 헤더 목록
# 프론트엔드에서 전송하는 모든 커스텀 헤더를 여기에 명시해야 합니다.
CORS_ALLOW_HEADERS = [
    'accept',              # 응답 형식 지정 (예: application/json)
    'accept-encoding',     # 압축 방식 (예: gzip, deflate)
    'authorization',       # JWT 토큰 전송 (예: Bearer <token>)
    'content-type',        # 요청 본문 형식 (예: application/json)
    'dnt',                 # Do Not Track
    'origin',              # 요청 출처
    'user-agent',          # 클라이언트 정보
    'x-csrftoken',         # CSRF 보호 토큰
    'x-requested-with',    # AJAX 요청 식별
]

# ==============================================
# drf-spectacular (Swagger/OpenAPI) 설정
# ==============================================
# API 문서 자동 생성 도구의 상세 설정
SPECTACULAR_SETTINGS = {
    'TITLE': 'Music Streaming & AI Generation API',
    'DESCRIPTION': '음악 스트리밍 및 AI 음악 생성 플랫폼 Backend API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # JWT 인증 스키마 설정
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
}