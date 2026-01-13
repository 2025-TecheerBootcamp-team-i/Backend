# 📁 프로젝트 파일 구조

> 마지막 업데이트: 2026-01-13 (리팩토링 완료)

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
│   ├── serializers.py       # DRF Serializers (JSON 직렬화)
│   ├── views.py             # API 뷰 (검색, 상세, 인증 등)
│   ├── urls.py              # URL 라우팅
│   ├── services.py          # 외부 API 서비스 (iTunes API)
│   ├── tests.py             # 테스트
│   └── migrations/          # DB 마이그레이션
│
├── 🐳 Dockerfile             # Docker 이미지 빌드 설정
├── 🐳 docker-compose.yml     # 멀티 컨테이너 오케스트레이션
│
├── 📋 requirements.txt       # Python 패키지 의존성
├── 📋 README.md              # 프로젝트 설명서
├── 📋 TREE.md                # 파일 구조 (현재 파일)
├── 📋 ITUNES_API_GUIDE.md    # iTunes API 통합 가이드
│
├── 🧪 test_itunes_api.py     # iTunes API 통합 테스트 스크립트
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
- [ ] **Phase 3-2**: 외부 API (LRCLIB) 및 비동기 작업 (Celery)
- [ ] **Phase 4**: 데이터 시각화 및 최적화 (play_log, 차트)
- [ ] **Phase 5**: 클라우드 이관 (AWS RDS, MQ, EC2)

## 📝 주요 변경사항

### 2026-01-13 - iTunes API 통합
- ✅ iTunes Search API 서비스 구현 (`music/services.py`)
- ✅ 고급 검색 문법 지원 (검색어 + 태그: `아이유#christmas`)
- ✅ 자동 DB 저장 (클릭 시 iTunes → DB 자동 저장)
- ✅ AI 필터링 (`exclude_ai` 파라미터)
- ✅ 새로운 API 엔드포인트:
  - `GET /api/v1/search?q={검색어}` - iTunes 기반 검색
  - `GET /api/v1/tracks/{itunes_id}` - 상세 조회 (자동 저장)

### 2026-01-13 - 리팩토링 완료
- ✅ `config/` 폴더 생성 및 설정 파일 이동
- ✅ `settings.py`, `urls.py`, `wsgi.py` → `config/`로 이동
- ✅ `asgi.py` 생성 (비동기 지원)
- ✅ `celery_app.py` → `config/celery.py`로 이동
- ✅ 모든 import 경로 업데이트 (`settings` → `config.settings`)
