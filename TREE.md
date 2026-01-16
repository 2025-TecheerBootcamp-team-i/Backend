# 📁 프로젝트 파일 구조

> 마지막 업데이트: 2026-01-15 (모니터링 시스템 구축 완료)

```
Backend/
├── 📄 manage.py              # Django 관리 명령어 진입점
│
├── 📂 config/                # Django 프로젝트 설정 폴더
│   ├── __init__.py          # config 패키지 초기화
│   ├── settings.py          # Django 설정 (DB, Celery, 환경변수 등)
│   ├── urls.py              # URL 라우팅 설정
│   ├── wsgi.py              # WSGI 애플리케이션 (배포용)
│   ├── asgi.py              # ASGI 애플리케이션 (비동기 지원)
│   └── celery.py            # Celery 비동기 작업 설정
│
├── 📂 music/                 # music 앱 (음악 도메인)
│   ├── __init__.py
│   ├── admin.py             # Django Admin 등록
│   ├── apps.py              # 앱 설정
│   ├── models.py            # 데이터 모델 (Music, Artists, Albums 등)
│   ├── urls.py              # URL 라우팅
│   ├── tests.py             # 테스트
│   │
│   ├── 📂 serializers/      # Serializers 모듈 (JSON 직렬화)
│   │   ├── __init__.py      # 모든 Serializer export
│   │   ├── base.py          # 기본 (Artist, Album, Tag, AiInfo)
│   │   ├── music.py         # 음악 관련 (MusicDetail, MusicLike)
│   │   ├── search.py        # 검색 관련 (iTunesSearchResult)
│   │   └── auth.py          # 인증 관련 (UserRegister, UserLogin)
│   │
│   ├── 📂 views/            # Views 모듈 (API 엔드포인트)
│   │   ├── __init__.py      # 모든 View export
│   │   ├── common.py        # 공통 유틸 (MusicPagination, ErrorTestView, DatabaseQueryTestView)
│   │   ├── auth.py          # 인증 관련 (Register, Login)
│   │   ├── likes.py         # 좋아요 관련 (MusicLike)
│   │   ├── search.py        # 검색 관련 (MusicSearch)
│   │   ├── music.py         # 음악 상세 관련 (MusicDetail)
│   │   ├── artists.py       # 아티스트 관련 (ArtistDetail, ArtistTracks, ArtistAlbums)
│   │   └── legacy.py        # 레거시 함수 기반 Views
│   │
│   ├── 📂 services/         # 외부 API 서비스
│   │   ├── __init__.py      # 모든 Service export
│   │   └── itunes.py        # iTunes API 통합
│   │
│   ├── 📂 music_generate/   # AI 음악 생성 모듈
│   │   ├── __init__.py
│   │   ├── exceptions.py    # Suno API 예외 클래스
│   │   ├── parsers.py       # JSON 파서 (FlexibleJSONParser)
│   │   ├── services.py      # LlamaService, SunoAPIService
│   │   └── utils.py         # 유틸리티 함수 (장르 추출 등)
│   │
│   ├── 📂 templates/        # Django 템플릿 (HTML)
│   │   └── music/
│   │       ├── music_generator.html  # 음악 생성 페이지
│   │       ├── music_list.html       # 음악 목록 페이지
│   │       └── monitor.html          # 음악 모니터링 페이지
│   │
│   ├── parsers.py           # 파서 re-export (하위 호환성)
│   ├── tasks.py             # Celery 비동기 작업 (generate_music_task)
│   ├── services.py          # 레거시 서비스 (하위 호환성)
│   ├── serializers.py       # 레거시 시리얼라이저 (하위 호환성)
│   │
│   └── 📂 migrations/       # DB 마이그레이션
│
├── 🐳 Dockerfile             # Docker 이미지 빌드 설정
├── 🐳 docker-compose.yml     # 멀티 컨테이너 오케스트레이션
│
├── 📋 requirements.txt       # Python 패키지 의존성
├── 📋 README.md              # 프로젝트 설명서
├── 📋 TREE.md                # 파일 구조 (현재 파일)
├── 📋 ITUNES_API_GUIDE.md    # iTunes API 통합 가이드
│
├── 📂 monitoring/            # 모니터링 시스템 설정
│   ├── prometheus.yml        # Prometheus 설정
│   ├── loki.yml              # Loki 설정
│   ├── promtail.yml          # Promtail 설정
│   ├── rabbitmq_enabled_plugins  # RabbitMQ Prometheus 플러그인
│   └── 📂 grafana/           # Grafana 설정
│       ├── provisioning/     # 데이터소스/대시보드 프로비저닝
│       │   ├── datasources/datasources.yml
│       │   └── dashboards/dashboards.yml
│       └── dashboards/       # 대시보드 JSON 파일
│           ├── django-metrics.json
│           ├── system-overview.json
│           └── rabbitmq-metrics.json
│
├── 🔒 .env                   # 환경 변수 (Git 제외)
├── 🔒 .env.example           # 환경 변수 템플릿 (팀 공유용)
└── 🔒 .gitignore             # Git 제외 파일 목록
```

## 📊 Phase 진행 상황

- [x] **Phase 1**: 로컬 올인원 환경 구축
- [x] **리팩토링**: config 폴더 구조로 정리
- [x] **Phase 2**: 인증 및 핵심 도메인 (User, Music, Playlist)
- [x] **Phase 3-1**: iTunes API 통합 (검색 우선 구조)
- [x] **앱 모듈화**: views/, serializers/, services/ 폴더 구조화
- [x] **Phase 3-2-1**: AI 음악 생성 (Suno API) 및 비동기 작업 (Celery)
- [x] **모니터링 시스템**: Prometheus, Grafana, Loki 통합 모니터링 구축
- [ ] **Phase 3-2-2**: 외부 API (LRCLIB) 통합
- [ ] **Phase 4**: 데이터 시각화 및 최적화 (play_log, 차트)
- [ ] **Phase 5**: 클라우드 이관 (AWS RDS, MQ, EC2)

## 📝 주요 변경사항

### 2026-01-13 - 앱 내부 모듈화
- ✅ `music/views/` 폴더 생성 (auth, likes, search, music)
- ✅ `music/serializers/` 폴더 생성 (base, music, search, auth)
- ✅ `music/services/` 폴더 생성 (itunes)
- ✅ `__init__.py`에서 모든 클래스 export (기존 import 호환)
- ✅ 기능별 파일 분리로 협업 충돌 감소

### 2026-01-13 - iTunes API 통합
- ✅ iTunes Search API 서비스 구현
- ✅ 고급 검색 문법 지원 (검색어 + 태그: `아이유 # christmas`)
- ✅ '# ' (해시+공백) 패턴만 태그로 인식 (C#, I'm #1 등 안전 처리)
- ✅ 자동 DB 저장 (클릭 시 iTunes → DB 자동 저장)
- ✅ AI 필터링 (`exclude_ai` 파라미터)

### 2026-01-13 - AI 음악 생성 기능
- ✅ `music_generate/` 모듈 생성 (LlamaService, SunoAPIService)
- ✅ Llama를 통한 한국어 → 영어 프롬프트 변환
- ✅ Suno API 통합 (음악 생성, 상태 조회, 웹훅 처리)
- ✅ Celery 비동기 작업 (`generate_music_task`)
- ✅ 예외 처리 (크레딧 부족, 인증 실패 등)
- ✅ 웹 UI 템플릿 (생성, 목록, 모니터링 페이지)

### API 엔드포인트

**인증 및 사용자**
- `POST /api/v1/auth/users/` - 회원가입
- `POST /api/v1/auth/tokens/` - 로그인
- `POST /api/v1/auth/refresh/` - 토큰 갱신

**음악 검색 및 조회**
- `GET /api/v1/search?q={검색어}` - iTunes 기반 검색
- `GET /api/v1/tracks/{itunes_id}` - 상세 조회 (자동 저장)
- `POST /api/v1/tracks/{music_id}/likes` - 좋아요 등록
- `DELETE /api/v1/tracks/{music_id}/likes` - 좋아요 취소

**AI 음악 생성**
- `POST /api/v1/generate/` - 음악 생성 (동기)
- `POST /api/v1/generate-async/` - 음악 생성 (비동기 - Celery)
- `GET /api/v1/task/{task_id}/` - 작업 상태 조회 (Celery)
- `GET /api/v1/suno-task/{task_id}/` - Suno API 작업 상태 조회
- `POST /api/v1/webhook/suno/` - Suno API 웹훅 (음악 생성 완료 콜백)

**테스트 엔드포인트 (모니터링용)**
- `GET /api/v1/test/error?code={500}&rate={0.5}` - 에러율 테스트
- `GET /api/v1/test/db?count={10}&type={all|select}` - DB 쿼리 테스트

**웹 페이지 (UI)**
- `GET /music/generator/` - 음악 생성 페이지
- `GET /music/list/` - 음악 목록 페이지
- `GET /music/monitor/{music_id}/` - 음악 모니터링 페이지

### 2026-01-13 - 리팩토링 완료
- ✅ `config/` 폴더 생성 및 설정 파일 이동
- ✅ `settings.py`, `urls.py`, `wsgi.py` → `config/`로 이동
- ✅ `asgi.py` 생성 (비동기 지원)
- ✅ `celery_app.py` → `config/celery.py`로 이동
- ✅ 모든 import 경로 업데이트 (`settings` → `config.settings`)

### 2026-01-15 - 모니터링 시스템 구축
- ✅ Prometheus, Grafana, Loki 통합 모니터링 스택 구축
- ✅ Django 메트릭 수집 (django-prometheus)
- ✅ RabbitMQ Prometheus 플러그인 활성화
- ✅ Grafana 대시보드 3개 자동 프로비저닝
  - Django Application Metrics (7개 패널)
  - System Overview (9개 패널)
  - RabbitMQ Metrics (10개 패널)
- ✅ 테스트 엔드포인트 추가
  - `/api/v1/test/error` - 에러율 테스트
  - `/api/v1/test/db` - DB 쿼리 테스트
- ✅ 모든 대시보드 쿼리에 "No data" 방지 처리 (`or vector(0)`)
