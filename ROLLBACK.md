# 🔄 배포 및 롤백 가이드

## 📋 자동 배포 플로우

### 전체 플로우 (CI/CD 자동화)

```
1. 코드 수정 → develop 브랜치 푸시 → PR 생성 → main 머지

2. GitHub Actions CI/CD 자동 실행:
   ├─ Docker 이미지 빌드
   ├─ Docker Hub에 푸시 (1.0.{PR_NUMBER} + latest)
   └─ EC2 SSH 접속 → docker compose pull → up -d (자동 배포)

3. 배포 완료! ✅
```

### GitHub Secrets 설정 필요

CI/CD 자동화를 위해 GitHub Repository Settings → Secrets에 다음을 등록해야 합니다:

- `DOCKER_HUB_USERNAME`: Docker Hub 사용자명
- `DOCKER_HUB_TOKEN`: Docker Hub 액세스 토큰
- `DOCKER_HUB_REPO`: Docker Hub 레포지토리명 (예: `2025_techeer_team_i`)
- `EC2_HOST`: EC2 퍼블릭 IP 또는 도메인
- `EC2_SSH_KEY`: EC2 접속용 SSH 프라이빗 키 (PEM 파일 내용)

### 수동 배포가 필요한 경우

GitHub Actions가 실패하거나 수동으로 배포해야 할 때:

```bash
# EC2에 SSH 접속
ssh ubuntu@{EC2_HOST}
cd /home/ubuntu/Backend

# 최신 이미지 pull (Docker Hub에서)
docker compose -f docker-compose.prod.yml pull

# 모든 서비스 재시작
docker compose -f docker-compose.prod.yml up -d --force-recreate

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f backend
```

---

## 🚨 긴급 롤백이 필요한 경우

### 상황: 새로 배포한 버전에 문제가 발생

**예시**: 1.0.55로 배포했는데 버그가 발견됨 → 1.0.54로 롤백

### 1단계: EC2 SSH 접속

```bash
ssh ubuntu@{EC2_HOST}
cd /home/ubuntu/Backend
```

### 2단계: 현재 실행 중인 버전 확인

```bash
# 컨테이너 상태 확인
docker compose -f docker-compose.prod.yml ps

# 현재 이미지 버전 확인
docker compose -f docker-compose.prod.yml images

# 정확한 버전 번호 확인 (latest가 실제로 몇 버전인지)
docker inspect hhyuninu/2025_techeer_team_i:latest | grep -A 1 "org.opencontainers.image.version"
```

**출력 예시**:
```json
"org.opencontainers.image.version": "1.0.54",
```

### 3단계: docker-compose.prod.yml에서 버전 고정

```bash
# latest → 1.0.54로 변경
sed -i 's/:latest/:1.0.54/g' docker-compose.prod.yml

# 변경 확인
grep "image:" docker-compose.prod.yml
```

**결과**:
```yaml
backend:
  image: hhyuninu/2025_techeer_team_i:1.0.54  # latest에서 1.0.54로 변경됨

celery:
  image: hhyuninu/2025_techeer_team_i:1.0.54

flower:
  image: hhyuninu/2025_techeer_team_i:1.0.54
```

### 4단계: 해당 버전으로 재배포

```bash
# 1.0.54 이미지 pull (Docker Hub에서)
docker compose -f docker-compose.prod.yml pull

# 모든 서비스 재시작 (backend, celery, flower, rabbitmq)
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### 5단계: 확인

```bash
# 컨테이너 상태 확인
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f backend

# API 동작 확인
curl -I https://api.brokencarrot.my/

# Flower 모니터링 확인 (선택사항)
curl -I http://{EC2_HOST}:5555/
```

### 6단계: 팀 공지

- Slack #backend-alerts 채널에 롤백 사실 공지
- 이슈 트래커에 롤백 사유 기록

---

## ✅ 문제 수정 후 최신 버전으로 복귀

### 방법 1: 자동 배포 (권장)

버그를 수정하고 main에 머지하면 **자동으로 새 버전이 배포**됩니다!

#### 1단계: 로컬에서 버그 수정

```bash
# 로컬 개발 환경에서
git checkout -b fix/bug-issue-description

# 버그 수정...
git add .
git commit -m "Fix: 버그 수정 내용"
git push origin fix/bug-issue-description
```

#### 2단계: PR 생성 & 머지

```
PR 생성 → 코드 리뷰 → develop 머지 → main 머지
↓
GitHub Actions CI/CD 자동 실행
↓
1. Docker 이미지 빌드 (1.0.56 + latest)
2. Docker Hub에 푸시
3. EC2 SSH 접속
4. docker compose pull (latest = 1.0.56)
5. docker compose up -d --force-recreate
↓
배포 완료! ✅
```

#### 3단계: EC2에서 latest로 복귀

⚠️ **중요**: 롤백 시 버전을 고정했다면, **반드시 latest로 되돌려야** 다음 배포가 자동으로 적용됩니다!

```bash
# EC2에 SSH 접속
ssh ubuntu@{EC2_HOST}
cd /home/ubuntu/Backend

# docker-compose.prod.yml에서 1.0.54 → latest로 변경
sed -i 's/:1.0.54/:latest/g' docker-compose.prod.yml

# 변경 확인
grep "image:" docker-compose.prod.yml
```

**결과**:
```yaml
backend:
  image: hhyuninu/2025_techeer_team_i:latest  # 1.0.54에서 latest로 복귀

celery:
  image: hhyuninu/2025_techeer_team_i:latest

flower:
  image: hhyuninu/2025_techeer_team_i:latest
```

이제 GitHub Actions가 자동으로 배포하므로 **수동 작업 불필요**합니다!

#### 4단계: GitHub Actions 로그 확인

GitHub Repository → Actions → 최신 워크플로우 확인

배포 성공 시:
- ✅ Build and Push Docker Image
- ✅ Deploy to EC2

#### 5단계: 최종 확인

```bash
# EC2에서 확인
ssh ubuntu@{EC2_HOST}
cd /home/ubuntu/Backend

# 컨테이너 상태 확인
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f backend

# API 동작 확인
curl -I https://api.brokencarrot.my/
```

---

### 방법 2: 수동 배포 (GitHub Actions 실패 시)

만약 GitHub Actions가 실패하거나 수동으로 배포해야 할 경우:

```bash
# EC2에 SSH 접속
ssh ubuntu@{EC2_HOST}
cd /home/ubuntu/Backend

# docker-compose.prod.yml을 latest로 변경 (아직 안 했다면)
sed -i 's/:1.0.54/:latest/g' docker-compose.prod.yml

# 최신 이미지 pull (latest = 1.0.56)
docker compose -f docker-compose.prod.yml pull

# 모든 서비스 재시작
docker compose -f docker-compose.prod.yml up -d --force-recreate

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f backend
```

✅ **이제 다음 배포부터는 자동으로 최신 버전이 반영됩니다!**

---

## 📊 버전 관리

### Docker Hub에서 버전 확인

- https://hub.docker.com/r/hhyuninu/2025_techeer_team_i/tags

### 버전 태그 규칙

- **PR #54** → 버전 **1.0.54**
- **PR #55** → 버전 **1.0.55**
- **latest** → 항상 최신 PR의 버전을 가리킴

### 예시

```
PR #53 머지 → 1.0.53 + latest (1.0.53)
PR #54 머지 → 1.0.54 + latest (1.0.54)  ← latest가 1.0.54로 업데이트
PR #55 머지 → 1.0.55 + latest (1.0.55)  ← latest가 1.0.55로 업데이트
```

---

## 🔍 트러블슈팅

### Q1. 특정 버전 번호를 모를 때

**방법 1: 이미지 라벨로 확인 (가장 쉬움)**:
```bash
# EC2에서
docker inspect hhyuninu/2025_techeer_team_i:latest | grep -A 4 "Labels"

# 또는 버전만 확인
docker inspect hhyuninu/2025_techeer_team_i:latest \
  | grep "org.opencontainers.image.version" \
  | cut -d'"' -f4
# 출력: 1.0.54
```

**방법 2: Docker Hub에서 확인**:
```bash
# 브라우저에서
https://hub.docker.com/r/hhyuninu/2025_techeer_team_i/tags
```

**방법 3: GitHub PR 번호로 확인**:
- GitHub PR 목록에서 마지막으로 머지된 PR 번호 확인
- 그 번호가 버전 번호

### Q2. 롤백 후에도 문제가 계속 발생할 때

```bash
# 1. 컨테이너 완전 중지
docker compose -f docker-compose.prod.yml down

# 2. 사용 중인 이미지 확인
docker images | grep 2025_techeer_team_i

# 3. 특정 버전 이미지 강제 재다운로드
docker pull hhyuninu/2025_techeer_team_i:1.0.54

# 4. 컨테이너 재시작
docker compose -f docker-compose.prod.yml up -d

# 5. 로그 확인
docker compose -f docker-compose.prod.yml logs -f
```

### Q3. 데이터베이스 마이그레이션 필요할 때

```bash
# 마이그레이션 적용
docker exec -it backend-backend-1 python manage.py migrate

# 마이그레이션 상태 확인
docker exec -it backend-backend-1 python manage.py showmigrations
```

### Q4. 환경변수 문제

`.env.production` 파일은 EC2 서버의 `/home/ubuntu/Backend/.env.production`에 저장되어 있습니다.

```bash
# 환경변수 확인
cat .env.production

# 컨테이너 내부의 환경변수 확인
docker exec backend-backend-1 env | grep SQL_
```

### Q5. RabbitMQ 연결 문제

```bash
# RabbitMQ 컨테이너 재시작
docker compose -f docker-compose.prod.yml restart rabbitmq

# RabbitMQ 로그 확인
docker compose -f docker-compose.prod.yml logs rabbitmq

# RabbitMQ 관리 UI 접속
http://{EC2_HOST}:15672/
# 기본 계정: guest / guest
```

---

## 📝 롤백 체크리스트

### 긴급 롤백 시

- [ ] EC2 SSH 접속
- [ ] 현재 버전 확인 (`docker compose images`)
- [ ] 롤백할 버전 번호 확인 (Docker Hub 또는 GitHub PR)
- [ ] `docker-compose.prod.yml`에서 `:latest` → `:1.0.XX` 변경
- [ ] `docker compose pull`
- [ ] `docker compose up -d --force-recreate`
- [ ] 로그 확인 및 API 테스트
- [ ] 팀원들에게 롤백 사실 공지 (Slack)
- [ ] 이슈 트래커에 롤백 사유 기록

### 정상화 시 (자동 배포)

- [ ] 로컬에서 버그 수정 완료
- [ ] PR 생성 및 코드 리뷰
- [ ] develop → main 머지
- [ ] GitHub Actions CI/CD 성공 확인
  - [ ] Build and Push 성공
  - [ ] Deploy to EC2 성공
- [ ] ⚠️ **중요**: EC2에서 `docker-compose.prod.yml`을 `:latest`로 변경 (롤백 시 버전 고정했다면)
- [ ] 최종 동작 확인 및 모니터링
- [ ] 팀원들에게 정상화 공지

---

## 🎯 베스트 프랙티스

### 1. 배포 전 체크리스트

```bash
# 로컬에서 테스트 완료
docker compose up --build
python manage.py test

# PR 리뷰 완료
# CI 통과 확인
# 팀원 승인 확인
```

### 2. 자동 배포 모니터링

```bash
# GitHub Actions 워크플로우 확인
# Repository → Actions → 최신 워크플로우

# 배포 후 EC2에서 로그 확인
ssh ubuntu@{EC2_HOST}
cd /home/ubuntu/Backend
docker compose -f docker-compose.prod.yml logs -f

# API 헬스체크
curl https://api.brokencarrot.my/health/  # (헬스체크 엔드포인트 있을 경우)

# Flower에서 Celery 작업 확인
http://{EC2_HOST}:5555/
```

### 3. 안전한 롤백

- **롤백은 최후의 수단**: 가능하면 Hotfix로 빠르게 수정
- **기록 남기기**: 모든 조치를 문서화
- **팀 커뮤니케이션**: 즉시 공유
- **근본 원인 분석**: 롤백 후 반드시 원인 파악 및 재발 방지
- **latest 복귀 필수**: 롤백 후 버전 고정 해제해야 다음 배포 자동 적용

### 4. 버전 관리 원칙

- **develop 브랜치**: 개발 중인 기능 통합
- **main 브랜치**: 프로덕션 배포용 (항상 안정적이어야 함)
- **hotfix 브랜치**: 긴급 버그 수정용 → **main에 머지하면 자동 배포**
- **feature 브랜치**: 새 기능 개발용

### 5. GitHub Secrets 보안

- **EC2_SSH_KEY**: 절대 Git에 커밋하지 마세요
- **주기적으로 갱신**: 3-6개월마다 SSH 키 교체 권장
- **최소 권한 원칙**: EC2 ubuntu 사용자에게 필요한 권한만 부여
- **접근 로그 모니터링**: EC2 접속 로그 주기적으로 확인

---

## 📞 긴급 연락

심각한 장애 발생 시:

1. **즉시 롤백 실행**
2. **Slack #backend-alerts 채널 공지**
3. **DevOps 담당자 연락**
4. **장애 대응 프로세스 시작**
5. **포스트모템 작성 및 공유**

---

## 📚 관련 문서

- [README.md](./README.md) - 전체 프로젝트 문서
- [docker-compose.prod.yml](./docker-compose.prod.yml) - 프로덕션 설정
- [.github/workflows/ci.yml](./.github/workflows/ci.yml) - CI 설정
