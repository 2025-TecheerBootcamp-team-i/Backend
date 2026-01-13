# 📁 프로젝트 파일 구조

> 마지막 업데이트: 2026-01-13 (차트 API 구현)

```
Backend/
├── 📄 manage.py              # Django 관리 명령어 진입점
│
├── 📂 config/                # Django 프로젝트 설정 폴더
│   ├── __init__.py          # config 패키지 초기화
│   ├── settings.py          # Django 설정 (DB, Celery Beat 스케줄 등)
│   ├── urls.py              # URL 라우팅 설정
│   ├── wsgi.py              # WSGI 애플리케이션 (배포용)
│   ├── asgi.py              # ASGI 애플리케이션 (비동기 지원)
│   └── celery.py            # Celery 비동기 작업 설정
│
├── 📂 music/                 # music 앱 (음악 도메인)
│   ├── __init__.py
│   ├── admin.py             # Django Admin 등록
│   ├── apps.py              # 앱 설정
│   ├── models.py            # 데이터 모델 (Music, Charts, PlayLogs 등)
│   ├── urls.py              # URL 라우팅
│   ├── tasks.py             # Celery 작업 (차트 계산, 데이터 정리)
│   ├── tests.py             # 테스트
│   │
│   ├── 📂 serializers/      # Serializers 모듈 (JSON 직렬화)
│   │   ├── __init__.py      # 모든 Serializer export
│   │   ├── base.py          # 기본 (Artist, Album, Tag, AiInfo)
│   │   ├── music.py         # 음악 관련 (MusicDetail, MusicLike)
│   │   ├── search.py        # 검색 관련 (iTunesSearchResult)
│   │   ├── auth.py          # 인증 관련 (UserRegister, UserLogin)
│   │   └── charts.py        # 차트 관련 (PlayLog, ChartItem, ChartResponse)
│   │
│   ├── 📂 views/            # Views 모듈 (API 엔드포인트)
│   │   ├── __init__.py      # 모든 View export
│   │   ├── common.py        # 공통 유틸 (MusicPagination)
│   │   ├── auth.py          # 인증 관련 (Register, Login)
│   │   ├── likes.py         # 좋아요 관련 (MusicLike)
│   │   ├── search.py        # 검색 관련 (MusicSearch)
│   │   ├── music.py         # 음악 상세 관련 (MusicDetail)
│   │   ├── playlogs.py      # 재생 기록 관련 (PlayLog)
│   │   └── charts.py        # 차트 관련 (Chart 조회)
│   │
│   ├── 📂 services/         # 외부 API 서비스
│   │   ├── __init__.py      # 모든 Service export
│   │   └── itunes.py        # iTunes API 통합
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
- [x] **Phase 4**: 차트 API 구현 (실시간/일일/AI 차트)
- [ ] **Phase 3-2**: 외부 API (LRCLIB) 및 비동기 작업 (Celery)
- [ ] **Phase 5**: 클라우드 이관 (AWS RDS, MQ, EC2)

## 📝 주요 변경사항

### 2026-01-13 - 차트 API 구현
- ✅ 실시간 차트 (10분마다, 최근 3시간 집계)
- ✅ 일일 차트 (매일 자정, 전날 전체 집계)
- ✅ AI 차트 (매일 자정, AI 곡만 집계)
- ✅ 재생 기록 API (POST /tracks/{id}/play)
- ✅ 차트 조회 API (GET /charts/{type})
- ✅ Celery Beat 스케줄 설정
- ✅ 데이터 정리 작업 (PlayLogs 90일, 실시간 차트 7일)

### 2026-01-13 - 앱 내부 모듈화
- ✅ `music/views/` 폴더 생성 (auth, likes, search, music, playlogs, charts)
- ✅ `music/serializers/` 폴더 생성 (base, music, search, auth, charts)
- ✅ `music/services/` 폴더 생성 (itunes)
- ✅ `__init__.py`에서 모든 클래스 export (기존 import 호환)
- ✅ 기능별 파일 분리로 협업 충돌 감소

### 2026-01-13 - iTunes API 통합
- ✅ iTunes Search API 서비스 구현
- ✅ 고급 검색 문법 지원 (검색어 + 태그: `아이유 # christmas`)
- ✅ '# ' (해시+공백) 패턴만 태그로 인식 (C#, I'm #1 등 안전 처리)
- ✅ 자동 DB 저장 (클릭 시 iTunes → DB 자동 저장)
- ✅ AI 필터링 (`exclude_ai` 파라미터)

### API 엔드포인트
- `GET /api/v1/search?q={검색어}` - iTunes 기반 검색
- `GET /api/v1/tracks/{itunes_id}` - 상세 조회 (자동 저장)
- `POST /api/v1/tracks/{music_id}/likes` - 좋아요 등록
- `DELETE /api/v1/tracks/{music_id}/likes` - 좋아요 취소
- `POST /api/v1/tracks/{music_id}/play` - 재생 기록 저장
- `GET /api/v1/charts/{type}` - 차트 조회 (realtime|daily|ai)
- `POST /api/v1/auth/users/` - 회원가입
- `POST /api/v1/auth/tokens/` - 로그인
- `POST /api/v1/auth/refresh/` - 토큰 갱신

### 2026-01-13 - 리팩토링 완료
- ✅ `config/` 폴더 생성 및 설정 파일 이동
- ✅ `settings.py`, `urls.py`, `wsgi.py` → `config/`로 이동
- ✅ `asgi.py` 생성 (비동기 지원)
- ✅ `celery_app.py` → `config/celery.py`로 이동
- ✅ 모든 import 경로 업데이트 (`settings` → `config.settings`)
