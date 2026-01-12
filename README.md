# 🎵 AI-Driven Music Insight & Streaming Platform (Backend)

## 1. 프로젝트 소개

**"음악을 듣는 것을 넘어, 눈으로 보다."**

본 프로젝트는 음악 스트리밍 로그 데이터를 시각화하여 트렌드와 패턴을 분석하는 AI 기반 음악 인사이트 플랫폼의 백엔드 레포지토리입니다.

- **주요 기능**: 고성능 음악 스트리밍 및 데이터 기반 인사이트 제공
- **대상 사용자**: 뮤지션, 크리에이터, 데이터 기반 트렌드 분석에 관심 있는 음악 애호가

---

## 2. 🛠️ 기술 스택

- **Backend**: Django, Django REST Framework, Celery
- **Database**: PostgreSQL
- **Message Broker**: RabbitMQ
- **DevOps & Infra**: Docker, Docker Compose
- **Workflow**: GitHub, Notion, Slack, Figma

---

## 3. 🚀 로컬 개발 환경 설정

프로젝트를 로컬 환경에서 실행하기 위한 가이드입니다.

### 사전 준비물

- Git
- Docker Desktop

### 설치 및 실행 단계

1.  **레포지토리 클론**
    ```bash
    git clone https://github.com/2025-TecheerBootcamp-team-i/demo-repository.git
    cd demo-repository
    ```

2.  **환경 변수 파일 확인**
    - 프로젝트 루트에 있는 `.env` 파일을 확인합니다. 로컬 개발에 필요한 모든 기본 설정이 이미 완료되어 있습니다.

3.  **Docker 컨테이너 실행**
    ```bash
    docker-compose up -d --build
    ```
    - 이 명령어로 웹 서버, 데이터베이스, 메시지 브로커, Celery 워커가 모두 백그라운드에서 실행됩니다.

4.  **데이터베이스 마이그레이션**
    - 컨테이너가 실행된 후, 데이터베이스에 필요한 테이블들을 생성해야 합니다.
    ```bash
    docker-compose exec web python manage.py migrate
    ```

5.  **관리자 계정 생성 (선택 사항)**
    - Django 관리자 페이지에 접속하기 위해 관리자 계정을 생성합니다.
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

6.  **서버 접속 확인**
    - **웹 애플리케이션**: `http://localhost:8000`
    - **Django 관리자 페이지**: `http://localhost:8000/admin`
    - **RabbitMQ 관리 페이지**: `http://localhost:15672` (ID: `guest`, PW: `guest`)

---

## 4. 🤝 협업 가이드

원활한 협업을 위해 다음 규칙을 준수해 주세요.

- **Git 브랜치 전략**: `feature/기능이름` 형식으로 브랜치를 생성하여 작업합니다. (예: `feature/user-login`)
- **커밋 메시지**: Conventional Commits 규칙을 따르는 것을 권장합니다. (예: `feat: 유저 로그인 기능 추가`)
- **Pull Request (PR)**: 작업 완료 후 `main` (또는 `develop`) 브랜치로 PR을 생성하고, 코드 리뷰를 거친 후 머지합니다.
- **소통**: 주요 논의는 Notion과 Slack을 통해 진행합니다.
