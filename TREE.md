# 📁 프로젝트 파일 구조

> 마지막 업데이트: 2026-01-12

```
Backend/
├── 📄 manage.py              # Django 관리 명령어 진입점
├── 📄 settings.py            # Django 설정 (DB, Celery, 환경변수 등)
├── 📄 urls.py                # URL 라우팅 설정
├── 📄 wsgi.py                # WSGI 애플리케이션 (배포용)
├── 📄 celery_app.py          # Celery 비동기 작업 설정
├── 📄 __init__.py            # Python 패키지 초기화
│
├── 🐳 Dockerfile             # Docker 이미지 빌드 설정
├── 🐳 docker-compose.yml     # 멀티 컨테이너 오케스트레이션
│
├── 📋 requirements.txt       # Python 패키지 의존성
├── 📋 README.md              # 프로젝트 설명서
├── 📋 TREE.md                # 파일 구조 (현재 파일)
│
├── 🔒 .env                   # 환경 변수 (Git 제외)
├── 🔒 .env.example           # 환경 변수 템플릿 (팀 공유용)
└── 🔒 .gitignore             # Git 제외 파일 목록
```

## 📊 Phase 진행 상황

- [x] **Phase 1**: 로컬 올인원 환경 구축
- [ ] **Phase 2**: 인증 및 핵심 도메인 (User, Music, Playlist)
- [ ] **Phase 3**: 외부 API 및 비동기 작업 (iTunes, LRCLIB, Celery)
- [ ] **Phase 4**: 데이터 시각화 및 최적화 (play_log, 차트)
- [ ] **Phase 5**: 클라우드 이관 (AWS RDS, MQ, EC2)
