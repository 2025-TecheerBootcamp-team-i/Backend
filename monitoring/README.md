# 🔍 모니터링 빠른 시작 가이드

## 📋 목차
1. [로컬 테스트](#로컬-테스트)
2. [프로덕션 배포](#프로덕션-배포)
3. [Grafana Cloud 대시보드 Import](#grafana-cloud-대시보드-import)
4. [CPU 스파이크 디버깅](#cpu-스파이크-디버깅)

---

## 🧪 로컬 테스트

### 1단계: 의존성 설치
```bash
pip install -r requirements.txt
```

### 2단계: 메트릭 엔드포인트 확인
```bash
# Django 서버 시작
python manage.py runserver

# 메트릭 확인 (새 터미널)
curl http://localhost:8000/metrics
```

다음과 같은 메트릭이 보이면 성공:
```
# HELP celery_tasks_total Total number of tasks executed
# TYPE celery_tasks_total counter
celery_tasks_total{status="success",task_name="music.tasks.update_realtime_chart"} 42.0

# HELP celery_task_duration_seconds Task execution time in seconds
# TYPE celery_task_duration_seconds histogram
celery_task_duration_seconds_bucket{le="0.1",task_name="music.tasks.update_realtime_chart"} 0.0
...
```

---

## 🚀 프로덕션 배포

### 1단계: Docker 이미지 빌드 및 푸시
```bash
# 이미지 빌드
docker build -t hhyuninu/2025_techeer_team_i:latest .

# Docker Hub에 푸시
docker push hhyuninu/2025_techeer_team_i:latest
```

### 2단계: 서버에서 재배포
```bash
# SSH로 서버 접속
ssh your-server

# 기존 컨테이너 중지 및 제거
docker-compose -f docker-compose.prod.yml down

# 최신 이미지 다운로드
docker-compose -f docker-compose.prod.yml pull

# 컨테이너 시작
docker-compose -f docker-compose.prod.yml up -d

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f backend celery
```

### 3단계: 메트릭 수집 확인
```bash
# Django 메트릭
curl http://localhost:8000/metrics

# RabbitMQ 메트릭
curl http://localhost:15692/metrics

# Grafana Agent 상태
docker logs grafana-agent --tail 50
```

---

## 📊 Grafana Cloud 대시보드 Import

### 방법 1: JSON 파일 Import (권장)

1. **Grafana Cloud 접속**
   - https://grafana.com 로그인
   - 대시보드 페이지로 이동

2. **대시보드 Import**
   - **Dashboards** → **Import** 클릭
   - **Upload JSON file** 선택
   - 다음 파일 중 하나를 업로드:
     - `monitoring/grafana/dashboards/celery-performance.json` (Celery 작업 모니터링)
     - `monitoring/grafana/dashboards/process-resources.json` (프로세스 리소스)
   - **Import** 클릭

3. **데이터소스 선택**
   - Prometheus 데이터소스 선택 (Grafana Cloud 기본 제공)
   - **Import** 클릭

4. **대시보드 확인**
   - 데이터가 표시되는지 확인
   - 데이터가 없다면 → [트러블슈팅](#트러블슈팅) 참고

### 방법 2: 수동 생성

상세한 가이드는 `docs/monitoring-guide.md`를 참고하세요.

---

## 🐛 CPU 스파이크 디버깅

### 즉시 실행 스크립트

```bash
# 서버에서 실행
./monitoring/debug_cpu_spike.sh
```

이 스크립트는 다음 정보를 출력합니다:
- ✅ 각 컨테이너의 CPU 사용량 상위 프로세스
- ✅ 현재 실행 중인 Celery 작업
- ✅ 최근 에러 로그
- ✅ 데이터베이스 연결 수
- ✅ 컨테이너별 리소스 사용량

### 결과 해석 예시

```
[backend 컨테이너]
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1 45.2  8.3 456789 123456 ?      Ssl  15:56   2:30 gunicorn: worker
root        12  8.1  6.2 345678  98765 ?      S    15:56   0:15 gunicorn: worker
```

**→ 해석:** 15:56에 gunicorn worker가 CPU 45.2% 사용 중
**→ 조치:** Django 엔드포인트에서 슬로우 쿼리 확인 필요

```
실행 중인 Celery 작업:
[{'name': 'music.tasks.update_realtime_chart', 'time_start': 1642956000}]
```

**→ 해석:** `update_realtime_chart` 작업이 실행 중
**→ 조치:** Grafana에서 작업 실행 시간 확인

---

## 🔧 트러블슈팅

### 문제 1: Grafana Cloud에 메트릭이 안 보임

**확인 사항:**
```bash
# 1. Grafana Agent 로그 확인
docker logs grafana-agent --tail 100

# 2. GRAFANA_CLOUD_TOKEN 환경변수 확인
docker exec grafana-agent env | grep GRAFANA_CLOUD_TOKEN

# 3. Prometheus 엔드포인트 수동 확인
curl http://localhost:8000/metrics | grep celery_tasks_total
```

**해결 방법:**
- `.env.production` 파일에 `GRAFANA_CLOUD_TOKEN`이 올바르게 설정되어 있는지 확인
- Grafana Agent를 재시작: `docker restart grafana-agent`

### 문제 2: Celery 메트릭이 0으로 표시됨

**원인:** Celery 작업이 아직 실행되지 않음

**해결 방법:**
```bash
# 1. Celery Beat 로그 확인 (스케줄러)
docker logs celery-beat --tail 50

# 2. 수동으로 작업 실행
docker exec celery celery -A config call music.tasks.test_task

# 3. 메트릭 재확인
curl http://localhost:8000/metrics | grep celery_tasks_total
```

### 문제 3: RabbitMQ 메트릭 수집 실패

**확인 사항:**
```bash
# RabbitMQ Prometheus 플러그인 활성화 확인
docker exec rabbitmq rabbitmq-plugins list

# 출력에서 [E*] rabbitmq_prometheus 확인
```

**해결 방법:**
```bash
# 플러그인 수동 활성화
docker exec rabbitmq rabbitmq-plugins enable rabbitmq_prometheus

# RabbitMQ 재시작
docker restart rabbitmq

# 메트릭 확인
curl http://localhost:15692/metrics
```

---

## 📈 권장 알림 설정

### Grafana Cloud Alert 생성

1. **Alerting** → **Alert rules** → **New alert rule** 클릭

2. **CPU 과부하 알림**
   - Query: `sum(rate(container_cpu_usage_seconds_total{name="backend"}[5m])) * 100 > 80`
   - Condition: `IS ABOVE 80 FOR 2m`
   - Notification: Slack/Email

3. **Celery 작업 실패 알림**
   - Query: `(sum(rate(celery_tasks_total{status="failure"}[5m])) / sum(rate(celery_tasks_total[5m]))) * 100 > 10`
   - Condition: `IS ABOVE 10 FOR 5m`
   - Notification: Slack/Email

4. **슬로우 쿼리 급증 알림**
   - Query: `increase(django_db_query_duration_seconds_count{le="2.0"}[5m]) > 50`
   - Condition: `IS ABOVE 50 FOR 2m`
   - Notification: Slack/Email

---

## 📚 추가 문서

- **상세 모니터링 가이드**: `docs/monitoring-guide.md`
- **Grafana 쿼리 예제**: `docs/monitoring-guide.md#grafana-cloud-대시보드-설정-가이드`
- **문제 해결 시나리오**: `docs/monitoring-guide.md#문제-해결-시나리오`

---

## 🆘 지원

문제가 해결되지 않으면:
1. Grafana Agent 로그 전체 확인: `docker logs grafana-agent > agent.log`
2. 모든 컨테이너 상태 확인: `docker ps -a`
3. 디버그 스크립트 결과 공유: `./monitoring/debug_cpu_spike.sh > debug.txt`
