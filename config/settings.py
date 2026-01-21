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
    'storages', # Django 파일 스토리지 백엔드 (S3 연동)
    'django_prometheus', # Prometheus 메트릭 노출 (모니터링)
    # Local apps
    'music', # 우리가 만든 'music' 앱 추가
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # Prometheus (맨 처음)
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS 미들웨어 (최상단 근처에 위치)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',  # Prometheus (맨 마지막)
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
        # django-prometheus를 사용하여 DB 쿼리 메트릭 수집
        'ENGINE': os.getenv('SQL_ENGINE', 'django_prometheus.db.backends.postgresql'),
        'NAME': os.getenv('SQL_DATABASE', 'music_db'),
        'USER': os.getenv('SQL_USER', 'music_user'),
        'PASSWORD': os.getenv('SQL_PASSWORD', 'music_password'),
        'HOST': os.getenv('SQL_HOST', 'db'), # docker-compose 서비스 이름
        'PORT': os.getenv('SQL_PORT', '5432'), # PostgreSQL 기본 포트
        'OPTIONS': {
            'sslmode': 'require',  # AWS RDS는 SSL 연결 필요
        } if os.getenv('SQL_HOST', '').endswith('.rds.amazonaws.com') else {},
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
CELERY_TIMEZONE = 'UTC'  # UTC 시간대 사용 (시간대 혼동 방지)
CELERY_ENABLE_UTC = True  # UTC 시간 사용

# ==============================================
# Celery Beat 스케줄 설정 (주기적 작업)
# ==============================================
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # 실시간 차트: 10분마다 갱신 (최근 3시간 집계)
    'update-realtime-chart': {
        'task': 'music.tasks.update_realtime_chart',
        'schedule': crontab(minute='*/10'),  # 매 10분마다
    },

    # 일일 차트: 매일 자정에 갱신 (전날 전체 집계)
    'update-daily-chart': {
        'task': 'music.tasks.update_daily_chart',
        'schedule': crontab(hour=0, minute=0),  # 매일 00:00
    },

    # AI 차트: 매일 자정에 갱신 (전날 AI 곡만 집계)
    'update-ai-chart': {
        'task': 'music.tasks.update_ai_chart',
        'schedule': crontab(hour=0, minute=5),  # 매일 00:05 (일일 차트와 약간 시차)
    },
    
    # 재생 기록 정리: 매일 새벽 2시 (90일 이전 삭제)
    'cleanup-old-playlogs': {
        'task': 'music.tasks.cleanup_old_playlogs',
        'schedule': crontab(hour=2, minute=0),  # 매일 02:00
    },
    
    # 실시간 차트 정리: 매일 새벽 3시 (7일 이전 삭제)
    'cleanup-old-realtime-charts': {
        'task': 'music.tasks.cleanup_old_realtime_charts',
        'schedule': crontab(hour=3, minute=0),  # 매일 03:00
    },
}

# ==============================================
# Django REST Framework 설정
# ==============================================
# REST API의 기본 인증 및 권한 설정을 정의합니다.
REST_FRAMEWORK = {
    # 기본 인증 방식: 커스텀 JWT 인증을 사용합니다.
    # Users 모델과 연동하여 JWT 토큰을 검증합니다.
    # 예: Authorization: Bearer <access_token>
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'music.authentication.CustomJWTAuthentication',  # 커스텀 JWT 인증
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
def spectacular_preprocessing_hook(endpoints):
    """
    drf-spectacular preprocessing hook
    api/music 경로의 엔드포인트 태그를 'Music API'로 통일
    """
    result = []
    for path, path_regex, method, callback in endpoints:
        # api/music 경로인 경우 태그를 'Music API'로 변경
        if path.startswith('/api/music/'):
            # callback에서 extend_schema 정보 확인
            if hasattr(callback, 'cls'):
                view_class = callback.cls
                # extend_schema 데코레이터 정보는 여기서 접근하기 어려우므로
                # 실제로는 view를 직접 수정하지 않고, 스키마 생성 후 처리
                pass
        result.append((path, path_regex, method, callback))
    return result


def spectacular_postprocessing_hook(result, generator, request, public):
    """
    drf-spectacular postprocessing hook
    - api/music 경로의 operation 태그를 'Music API'로 변경
    - /music/ 경로의 operation 태그를 '웹'으로 변경
    - /api/v1/tracks/ 경로의 'tracks' 태그를 제거하고 재생 관련은 '음악 재생'으로 변경
    """
    # paths에서 경로별로 태그 변경
    if 'paths' in result:
        for path, methods in result['paths'].items():
            # /api/music/로 시작하는 경로 → 'Music API' 태그
            if path.startswith('/api/music/'):
                for method in methods.values():
                    if isinstance(method, dict) and 'tags' in method:
                        if method['tags']:
                            method['tags'] = ['Music API']
            # /music/로 시작하는 경로 → '웹' 태그 (단, /music/로 시작하지만 /music/api/ 같은 것은 제외)
            elif path.startswith('/music/') and not path.startswith('/music/api/'):
                for method in methods.values():
                    if isinstance(method, dict) and 'tags' in method:
                        if method['tags']:
                            method['tags'] = ['웹']
            # /api/v1/tracks/ 경로 처리: 'tracks' 태그 제거 및 재생 관련은 '음악 재생'으로
            elif path.startswith('/api/v1/tracks/'):
                for method_name, method in methods.items():
                    if isinstance(method, dict) and 'tags' in method:
                        tags = method['tags']
                        # 'tracks' 태그가 있으면 제거
                        if 'tracks' in tags:
                            tags.remove('tracks')
                        # 재생 관련 경로(/play)는 '음악 재생' 태그로 변경
                        if '/play' in path:
                            if '음악 재생' not in tags:
                                tags.append('음악 재생')
                        # 태그가 비어있으면 기본 태그 유지 (각 View에서 설정한 태그)
                        if not tags and method.get('tags'):
                            # 원래 태그가 있으면 유지
                            pass
            # /api/v1/generate/, /api/v1/generate-async/, /api/v1/suno-task/ 경로 처리: 모두 '음악 생성' 태그로 통일
            elif path.startswith('/api/v1/generate/') or path.startswith('/api/v1/generate-async/') or path.startswith('/api/v1/suno-task/'):
                for method_name, method in methods.items():
                    if isinstance(method, dict) and 'tags' in method:
                        # 다른 태그는 모두 제거하고 '음악 생성' 태그만 유지
                        method['tags'] = ['음악 생성']
            # /api/v1/task/ 경로 처리: 'task' 태그 제거하고 '작업 상태 조회'로 변경
            elif path.startswith('/api/v1/task/'):
                for method_name, method in methods.items():
                    if isinstance(method, dict) and 'tags' in method:
                        tags = method['tags']
                        # 'task' 태그가 있으면 제거
                        if 'task' in tags:
                            tags.remove('task')
                        # '작업 상태 조회' 태그 추가
                        if '작업 상태 조회' not in tags:
                            tags.append('작업 상태 조회')
                        # 태그가 비어있으면 '작업 상태 조회'로 설정
                        if not tags:
                            method['tags'] = ['작업 상태 조회']
            # /api/v1/webhook/ 경로 처리: 'Webhook' 태그 제거하고 '음악 생성'으로 변경
            elif path.startswith('/api/v1/webhook/'):
                for method_name, method in methods.items():
                    if isinstance(method, dict) and 'tags' in method:
                        tags = method['tags']
                        # 'Webhook', 'webhook' 태그가 있으면 제거
                        if 'Webhook' in tags:
                            tags.remove('Webhook')
                        if 'webhook' in tags:
                            tags.remove('webhook')
                        # '음악 생성' 태그 추가
                        if '음악 생성' not in tags:
                            tags.append('음악 생성')
                        # 태그가 비어있으면 '음악 생성'으로 설정
                        if not tags:
                            method['tags'] = ['음악 생성']
    
    # 모든 경로에서 'default' 태그가 있는 경우 '음악 조회'로 변경 (별도 루프로 처리)
    # 이 루프는 모든 경로를 다시 순회하여 'default' 태그를 확실히 제거
    if 'paths' in result:
        for path, methods in result['paths'].items():
            for method_name, method in methods.items():
                if isinstance(method, dict):
                    # 'tags' 키가 없으면 생성
                    if 'tags' not in method:
                        method['tags'] = []
                    
                    tags = method.get('tags', [])
                    # None이거나 빈 값인 경우 빈 리스트로 설정
                    if tags is None:
                        tags = []
                    # 리스트가 아닌 경우 리스트로 변환
                    if not isinstance(tags, list):
                        tags = [tags] if tags else []
                    
                    # 'default' 태그 제거 (대소문자 구분 없이, 모든 변형 체크)
                    filtered_tags = []
                    has_default = False
                    for tag in tags:
                        # 문자열로 변환하여 비교
                        tag_str = str(tag).strip().lower()
                        # 'default'의 모든 변형 체크
                        if tag_str in ['default', 'defaults', 'default tag']:
                            has_default = True
                        else:
                            filtered_tags.append(tag)
                    
                    # 'default' 태그가 있었거나 태그가 비어있는 경우
                    if has_default:
                        # '음악 조회' 태그 추가 (없는 경우에만)
                        if '음악 조회' not in filtered_tags:
                            filtered_tags.insert(0, '음악 조회')  # 맨 앞에 추가
                        # 태그 리스트 완전히 교체
                        method['tags'] = filtered_tags
                    elif not filtered_tags:
                        # 태그가 비어있으면 '음악 조회'로 설정
                        method['tags'] = ['음악 조회']
                    else:
                        # 'default'가 없어도 태그 리스트 업데이트
                        method['tags'] = filtered_tags
    return result


SPECTACULAR_SETTINGS = {
    'TITLE': 'Music Streaming & AI Generation API',
    'DESCRIPTION': '음악 스트리밍 및 AI 음악 생성 플랫폼 Backend API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # JWT 인증 스키마 설정
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    # 태그 순서 정의 (Swagger UI에서 태그가 이 순서로 표시됨)
    'TAGS': [
        {'name': '웹'},
        {'name': 'Music API'},
        {'name': '인증'},
        {'name': '검색'},
        {'name': '음악 상세'},
        {'name': '음악 재생'},
        {'name': '음악 조회'},
        {'name': '좋아요'},
        {'name': '아티스트'},
        {'name': '사용자 통계'},
        {'name': '플레이리스트'},
        {'name': '음악 생성'},
        {'name': '작업 상태 조회'},
        {'name': '테스트'},
    ],
    # api/music 경로의 태그를 'Music API'로 통일
    'POSTPROCESSING_HOOKS': [
        'config.settings.spectacular_postprocessing_hook',
    ],

    'APPEND_COMPONENTS': {
        "securitySchemes": {
            "jwtAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    'SECURITY': [{"jwtAuth": []}],
}

# ==============================================
# AWS S3 파일 스토리지 설정
# ==============================================
# AWS S3를 기본 파일 스토리지로 사용 (버킷 이름이 설정된 경우)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'ap-northeast-2')
AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN', f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com')

# S3 버킷이 설정된 경우에만 S3를 기본 스토리지로 사용
# 단, DEBUG 모드에서는 로컬 정적 파일 스토리지 사용 (개발 편의성)
if AWS_STORAGE_BUCKET_NAME and not DEBUG:
    # 프로덕션: S3 스토리지 사용
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    
    # S3 설정
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # 1일 캐시
    }
    AWS_DEFAULT_ACL = 'public-read'  # 퍼블릭 읽기 허용
    AWS_QUERYSTRING_AUTH = False  # URL에 서명 불필요 (퍼블릭 파일)
else:
    # 개발 환경 또는 S3 미설정: 로컬 스토리지 사용
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

