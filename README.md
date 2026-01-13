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
- **AI**: LangChain + Llama (via Tailscale), Suno API
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

2.  **환경 변수 파일 생성**
    ```bash
    cp .env.example .env
    ```
    
    `.env` 파일을 열어서 필요한 값들을 설정하세요:
    - `SECRET_KEY`: Django 시크릿 키 (프로덕션에서는 반드시 변경!)
    - `NGROK_AUTHTOKEN`: ngrok 인증 토큰 (웹훅 콜백 사용 시 필요)
    - `SUNO_API_KEY`: Suno API 키 (음악 생성 기능 사용 시 필요)
    - `WINDOWS_LLAMA_IP`: Llama 서버 IP (음악 생성 기능 사용 시 필요)

3.  **Docker 컨테이너 실행**
   
   **기본 실행 (ngrok 없이):**
   ```bash
   docker-compose up -d --build
   ```
   
   **ngrok 포함 실행 (웹훅 콜백 사용 시):**
   ```bash
   docker-compose --profile ngrok up -d --build
   ```
   
   이 명령어로 다음 서비스들이 실행됩니다:
   - 웹 서버 (Django): `http://localhost:8000`
   - 데이터베이스 (PostgreSQL): `localhost:5433`
   - 메시지 브로커 (RabbitMQ): `localhost:5672`, 관리 UI: `http://localhost:15672`
   - Celery 워커 (비동기 작업 처리)
   - ngrok (선택적): `http://localhost:4040`

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

## 4. 🎵 AI 음악 생성 기능

### 개요

사용자가 한국어 프롬프트를 입력하면, Llama AI가 이를 Suno API용 영어 프롬프트로 변환하고, Suno API를 통해 실제 음악을 생성합니다.

### 아키텍처 흐름

```
사용자 입력 → Django API → Llama (Windows via Tailscale) → Suno API → 음악 생성
```

### 환경 변수 설정

`.env` 파일에 다음 환경 변수를 추가해야 합니다:

```bash
# Llama 설정 (Tailscale을 통한 Windows 연결)
WINDOWS_LLAMA_IP=100.92.0.45
LLAMA_MODEL_NAME=llama3.1:8b-instruct-q8_0

# Suno API 설정
SUNO_API_KEY=your_suno_api_key_here  # https://sunoapi.org/ko 에서 발급
SUNO_API_URL=https://api.sunoapi.org/v1
SUNO_CALLBACK_URL=https://your-public-url.com/api/music/webhook/suno/  # Webhook 콜백 URL
```

### Suno API 키 발급 방법

1. [sunoapi.org](https://sunoapi.org/ko) 접속
2. 회원가입 및 로그인
3. 대시보드에서 API 키 발급
4. `.env` 파일의 `SUNO_API_KEY`에 발급받은 키 입력

### Webhook 콜백 URL 설정

Suno API는 음악 생성이 완료되면 콜백 URL로 결과를 전송합니다. 로컬 개발 환경에서는 터널링 서비스를 사용해야 합니다.

#### 방법 1: Docker로 ngrok 사용 (권장)

Docker 환경에 ngrok이 통합되어 있어 별도 설치 없이 사용할 수 있습니다.

1. **Ngrok 계정 생성 및 토큰 발급**
   - https://dashboard.ngrok.com/signup 에서 계정 생성
   - https://dashboard.ngrok.com/get-started/your-authtoken 에서 인증 토큰 발급

2. **환경 변수 설정**
   ```bash
   # .env 파일에 추가
   NGROK_AUTHTOKEN=your_ngrok_authtoken_here
   ```

3. **Ngrok과 함께 서버 시작**
   ```bash
   # ngrok 프로필을 포함하여 실행
   docker-compose --profile ngrok up -d
   ```

4. **Ngrok URL 확인**
   - **간편한 방법 (스크립트 사용)**:
     ```bash
     ./get_ngrok_url.sh
     ```
   - **ngrok 웹 UI**: http://localhost:4040 에서 터널 상태 확인
   - **터널 URL 확인 (수동)**:
     ```bash
     curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
     ```

5. **콜백 URL 설정**
   - 확인한 ngrok URL을 `.env` 파일에 추가:
     ```bash
     SUNO_CALLBACK_URL=https://xxxxx.ngrok.io/api/v1/webhook/suno/
     ```
   - 서버 재시작:
     ```bash
     docker-compose restart web
     ```

#### 방법 1-1: 호스트에서 ngrok 직접 실행 (대안)

Docker 없이 호스트에서 직접 실행하려면:

1. **ngrok 설치**
   ```bash
   # macOS
   brew install ngrok
   ```

2. **인증 토큰 설정**
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

3. **ngrok 실행**
   ```bash
   ngrok http 8000
   ```

#### 방법 2: 다른 터널링 서비스

- **localtunnel**: `npx localtunnel --port 8000`
  - ⚠️ **주의**: localtunnel은 비밀번호 게이트가 있어 webhook이 차단될 수 있습니다
  - 비밀번호는 공인 IP 주소입니다 (`https://loca.lt/mytunnelpassword`)
  - Suno API가 브라우저 User-Agent를 사용하면 401 오류 발생 가능
  - **권장하지 않음**: webhook용으로는 ngrok 사용 권장
- **serveo**: `ssh -R 80:localhost:8000 serveo.net`
- **cloudflared**: `cloudflared tunnel --url http://localhost:8000`

#### 주의사항

- ⚠️ 터널링 서비스는 프로세스가 실행 중일 때만 작동합니다
- ⚠️ 터널이 끊기면 webhook을 받을 수 없습니다 (Polling으로 대체)
- ⚠️ 프로덕션 환경에서는 실제 공개 URL을 사용하세요

### 사전 요구사항

- **Windows에서 Ollama 실행**: Llama 모델이 Windows 로컬에서 실행 중이어야 합니다
- **Tailscale VPN**: Mac과 Windows 간 연결을 위해 Tailscale이 활성화되어 있어야 합니다
- **Suno API 크레딧**: 음악 생성을 위한 Suno API 크레딧이 필요합니다

### 웹 UI 사용 (권장)

음악 생성을 위한 웹 인터페이스가 제공됩니다. 브라우저에서 다음 URL로 접속하여 사용하세요:

**음악 생성 페이지**: http://localhost:8000/music/generator/

웹 UI에서 다음 작업을 수행할 수 있습니다:
- 한국어 프롬프트 입력
- 음악 생성 요청
- 생성된 음악 목록 확인
- 음악 재생 및 다운로드

> 💡 **권장**: 웹 UI를 사용하면 API 호출 없이 간편하게 음악을 생성할 수 있습니다.

### API 사용 예시

#### 1. 동기 방식 (즉시 결과 반환)

```bash
curl -X POST http://localhost:8000/api/music/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "여름의 장미",
    "user_id": 1,
    "make_instrumental": false
  }'
```

**응답 예시:**
```json
{
  "music_id": 123,
  "music_name": "Summer Roses",
  "audio_url": "https://cdn.suno.ai/xxxxx.mp3",
  "is_ai": true,
  "genre": "K-Pop",
  "duration": 180,
  "ai_info": [
    {
      "aiinfo_id": 1,
      "input_prompt": "Original: 여름의 장미\nConverted: Context: Summer roses blooming...",
      "created_at": "2026-01-13T10:30:00Z"
    }
  ],
  "created_at": "2026-01-13T10:30:00Z"
}
```

#### 2. 비동기 방식 (Celery 사용)

음악 생성은 20-30초가 소요될 수 있으므로, 비동기 방식을 권장합니다.

**음악 생성 요청:**
```bash
curl -X POST http://localhost:8000/api/music/generate-async/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "밤하늘의 별",
    "user_id": 1
  }'
```

**응답:**
```json
{
  "task_id": "abc123-def456",
  "status": "pending",
  "message": "음악 생성이 시작되었습니다. task_id로 상태를 확인하세요."
}
```

**작업 상태 확인:**
```bash
curl http://localhost:8000/api/music/task/abc123-def456/
```

**완료 시 응답:**
```json
{
  "task_id": "abc123-def456",
  "status": "SUCCESS",
  "result": {
    "success": true,
    "music_id": 124,
    "music_name": "Starry Night",
    "audio_url": "https://cdn.suno.ai/yyyyy.mp3"
  },
  "error": null
}
```

#### 3. 음악 목록 조회

```bash
# 모든 음악 조회
curl http://localhost:8000/api/music/

# AI 생성 음악만 필터링
curl http://localhost:8000/api/music/?is_ai=true

# 특정 사용자의 음악 조회
curl http://localhost:8000/api/music/?user_id=1
```

#### 4. 음악 상세 조회

```bash
curl http://localhost:8000/api/music/123/
```

### API 엔드포인트 목록

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/music/generate/` | AI 음악 생성 (동기) |
| POST | `/api/music/generate-async/` | AI 음악 생성 (비동기) |
| GET | `/api/music/task/{task_id}/` | 작업 상태 조회 |
| GET | `/api/music/` | 음악 목록 조회 |
| GET | `/api/music/{music_id}/` | 음악 상세 조회 |

### 주의사항

- 음악 생성은 한 번에 약 20-30초가 소요됩니다
- Suno API는 유료 서비스이므로 크레딧 소진에 유의하세요
- Windows에서 Ollama가 실행 중이지 않으면 프롬프트 변환이 실패합니다
- Tailscale VPN이 비활성화되면 Llama 연결이 끊어집니다

### 트러블슈팅

**"Llama 연결 실패" 오류:**
- Windows에서 Ollama가 실행 중인지 확인
- Tailscale VPN이 활성화되어 있는지 확인
- `WINDOWS_LLAMA_IP` 환경 변수가 올바른지 확인

**"Suno API 연결 실패" 오류:**
- `SUNO_API_KEY`가 올바르게 설정되었는지 확인
- Suno API 크레딧이 남아있는지 확인
- 네트워크 연결 상태 확인

---

## 5. 🤝 협업 가이드

원활한 협업을 위해 다음 규칙을 준수해 주세요.

- **Git 브랜치 전략**: `feature/기능이름` 형식으로 브랜치를 생성하여 작업합니다. (예: `feature/user-login`)
- **커밋 메시지**: Conventional Commits 규칙을 따르는 것을 권장합니다. (예: `feat: 유저 로그인 기능 추가`)
- **Pull Request (PR)**: 작업 완료 후 `main` (또는 `develop`) 브랜치로 PR을 생성하고, 코드 리뷰를 거친 후 머지합니다.
- **소통**: 주요 논의는 Notion과 Slack을 통해 진행합니다.
