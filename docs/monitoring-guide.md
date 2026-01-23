# 🔍 모니터링 가이드

## CPU 스파이크 원인 진단 방법

### 1. 즉시 확인 (서버에서 실행)

```bash
# CPU 스파이크 디버깅 스크립트 실행
./monitoring/debug_cpu_spike.sh
```

이 스크립트는 다음 정보를 제공합니다:
- 각 컨테이너의 CPU 사용량 상위 프로세스
- 현재 실행 중인 Celery 작업
- 최근 에러 로그
- 데이터베이스 연결 수
- 컨테이너별 리소스 사용량

### 2. Grafana Cloud에서 확인

Grafana Cloud 대시보드에서 다음을 확인하세요:
1. **System Overview** → CPU 사용량 타임라인
2. **Django Metrics** → 엔드포인트별 요청 수와 응답 시간
3. **Celery Metrics** → 작업별 실행 시간과 실패율

---

## 📊 Grafana Cloud 대시보드 설정 가이드

### 1단계: Grafana Cloud 접속

1. https://grafana.com 접속
2. 로그인 후 대시보드로 이동

### 2단계: 새 대시보드 만들기

#### A. Celery 작업 모니터링 대시보드

1. **Dashboards** → **New** → **New Dashboard** 클릭
2. **Add visualization** 클릭
3. 다음 패널들을 추가:

**패널 1: Celery 작업 실행 시간**
```promql
# Query
histogram_quantile(0.95, sum(rate(celery_task_duration_seconds_bucket[5m])) by (task_name, le))

# 패널 설정
- Title: Celery 작업 실행 시간 (95th percentile)
- Legend: {{ task_name }}
- Unit: seconds (s)
- Panel type: Time series
```

**패널 2: Celery 작업 성공/실패율**
```promql
# Query 1 (성공)
sum(rate(celery_tasks_total{status="success"}[5m])) by (task_name)

# Query 2 (실패)
sum(rate(celery_tasks_total{status="failure"}[5m])) by (task_name)

# 패널 설정
- Title: Celery 작업 성공/실패율
- Legend: {{ task_name }} - {{ status }}
- Unit: ops (operations per second)
- Panel type: Time series
```

**패널 3: 현재 실행 중인 작업 수**
```promql
# Query
sum(celery_tasks_running) by (task_name)

# 패널 설정
- Title: 실행 중인 Celery 작업
- Legend: {{ task_name }}
- Panel type: Time series
```

**패널 4: 작업별 총 실행 횟수**
```promql
# Query
sum(celery_tasks_total) by (task_name, status)

# 패널 설정
- Title: Celery 작업 총 실행 횟수
- Legend: {{ task_name }} - {{ status }}
- Panel type: Bar chart
```

#### B. Django 성능 모니터링 대시보드

**패널 1: 엔드포인트별 요청 수**
```promql
# Query
sum(rate(django_http_requests_total_by_view_transport_method_total[5m])) by (view)

# 패널 설정
- Title: 엔드포인트별 요청 수 (초당)
- Legend: {{ view }}
- Unit: req/s
- Panel type: Time series
```

**패널 2: 응답 시간 (95th percentile)**
```promql
# Query
histogram_quantile(0.95, 
  sum(rate(django_http_requests_latency_seconds_by_view_method_bucket[5m])) 
  by (view, le)
)

# 패널 설정
- Title: 응답 시간 (95th percentile)
- Legend: {{ view }}
- Unit: seconds (s)
- Panel type: Time series
```

**패널 3: 슬로우 쿼리 (2초 이상)**
```promql
# Query
sum(rate(django_db_query_duration_seconds_bucket{le="2.0"}[5m]))

# 패널 설정
- Title: 슬로우 쿼리 (2초 이상)
- Unit: queries/s
- Panel type: Stat
- Thresholds: 
  - Green: 0-5
  - Yellow: 5-10
  - Red: >10
```

**패널 4: 데이터베이스 연결 수**
```promql
# Query
django_db_new_connections_total

# 패널 설정
- Title: 데이터베이스 연결 수
- Panel type: Time series
```

#### C. 프로세스별 리소스 사용량 대시보드

**패널 1: 컨테이너별 CPU 사용량**
```promql
# Query
sum(rate(container_cpu_usage_seconds_total{name=~"backend|celery|celery-beat|rabbitmq"}[5m])) 
by (name) * 100

# 패널 설정
- Title: 컨테이너별 CPU 사용량
- Legend: {{ name }}
- Unit: percent (0-100)
- Panel type: Time series
```

**패널 2: 컨테이너별 메모리 사용량**
```promql
# Query
sum(container_memory_usage_bytes{name=~"backend|celery|celery-beat|rabbitmq"}) 
by (name) / 1024 / 1024

# 패널 설정
- Title: 컨테이너별 메모리 사용량
- Legend: {{ name }}
- Unit: megabytes (MB)
- Panel type: Time series
```

**패널 3: 프로세스별 CPU Top 10**
```promql
# Query
topk(10, 
  rate(container_cpu_usage_seconds_total[5m]) * 100
)

# 패널 설정
- Title: CPU 사용량 상위 10개 프로세스
- Panel type: Bar gauge
```

**패널 4: 네트워크 I/O**
```promql
# Query 1 (수신)
sum(rate(container_network_receive_bytes_total{name=~"backend|celery"}[5m])) 
by (name)

# Query 2 (송신)
sum(rate(container_network_transmit_bytes_total{name=~"backend|celery"}[5m])) 
by (name)

# 패널 설정
- Title: 네트워크 I/O
- Legend: {{ name }} - {{ direction }}
- Unit: bytes/sec
- Panel type: Time series
```

### 3단계: 알림 설정 (Alert Rules)

CPU 스파이크 발생 시 즉시 알림을 받도록 설정:

**알림 1: CPU 사용량 80% 이상**
```promql
# Query
sum(rate(container_cpu_usage_seconds_total{name="backend"}[5m])) * 100 > 80

# 알림 설정
- Name: Backend CPU High
- Condition: WHEN last() OF query(A) IS ABOVE 80
- For: 2m (2분 이상 지속 시)
- Message: 백엔드 CPU 사용량이 80%를 초과했습니다!
```

**알림 2: 메모리 사용량 80% 이상**
```promql
# Query
(container_memory_usage_bytes{name="backend"} / 
 container_spec_memory_limit_bytes{name="backend"}) * 100 > 80

# 알림 설정
- Name: Backend Memory High
- Condition: WHEN last() OF query(A) IS ABOVE 80
- For: 5m
- Message: 백엔드 메모리 사용량이 80%를 초과했습니다!
```

**알림 3: Celery 작업 실패율 높음**
```promql
# Query
(sum(rate(celery_tasks_total{status="failure"}[5m])) / 
 sum(rate(celery_tasks_total[5m]))) * 100 > 10

# 알림 설정
- Name: Celery Task Failure Rate High
- Condition: WHEN last() OF query(A) IS ABOVE 10
- For: 5m
- Message: Celery 작업 실패율이 10%를 초과했습니다!
```

**알림 4: 슬로우 쿼리 급증**
```promql
# Query
increase(django_db_query_duration_seconds_count{le="2.0"}[5m]) > 50

# 알림 설정
- Name: Slow Queries Spike
- Condition: WHEN last() OF query(A) IS ABOVE 50
- For: 2m
- Message: 슬로우 쿼리가 급증했습니다! (5분간 50개 이상)
```

### 4단계: 알림 채널 연동

1. **Alerting** → **Contact points** 이동
2. **Add contact point** 클릭
3. 선택 가능한 옵션:
   - **Slack**: Webhook URL 입력
   - **Email**: 이메일 주소 입력
   - **Discord**: Webhook URL 입력
   - **Telegram**: Bot Token과 Chat ID 입력

---

## 🔧 문제 해결 시나리오

### 시나리오 1: 실시간 차트 업데이트 시 CPU 급증

**증상:**
- 매 10분마다 (X:00, X:10, X:20...) CPU 사용량 급증
- Grafana에서 `update_realtime_chart` 작업 실행 시간이 긴 것 확인

**해결 방법:**

1. **PlayLogs 테이블 인덱싱 확인**
```bash
docker exec backend python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('''
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'music_playlogs'
    ''')
    for row in cursor.fetchall():
        print(row)
"
```

2. **차트 업데이트 쿼리 최적화** (music/tasks/charts.py 수정)
```python
# 현재: 모든 로그를 집계
results = PlayLogs.objects.filter(
    played_at__gte=start_time,
    played_at__lt=now,
    is_deleted=False
).values('music_id').annotate(
    play_count=Count('play_log_id')
).order_by('-play_count')[:100]

# 개선: 인덱스를 활용한 쿼리
results = PlayLogs.objects.filter(
    played_at__gte=start_time,
    played_at__lt=now,
    is_deleted=False
).values('music_id').annotate(
    play_count=Count('play_log_id')
).order_by('-play_count')[:100].select_related('music')
```

3. **Celery 워커 동시성 증가** (docker-compose.prod.yml 수정)
```yaml
celery:
  command: celery -A config worker -l info --concurrency=2  # 1 → 2로 증가
```

### 시나리오 2: AI 음악 생성 시 메모리 부족

**증상:**
- `generate_music_task` 실행 시 메모리 사용량 급증
- SWAP 사용량 증가

**해결 방법:**

1. **메모리 제한 증가** (docker-compose.prod.yml)
```yaml
celery:
  deploy:
    resources:
      limits:
        memory: 512M  # 350M → 512M
```

2. **AI 작업 전용 큐 생성** (config/settings.py)
```python
CELERY_TASK_ROUTES = {
    'music.tasks.generate_music_task': {'queue': 'ai_queue'},
    'music.tasks.*': {'queue': 'default'},
}
```

3. **AI 전용 워커 추가** (docker-compose.prod.yml)
```yaml
celery-ai:
  image: hhyuninu/2025_techeer_team_i:latest
  command: celery -A config worker -Q ai_queue -l info --concurrency=1
  deploy:
    resources:
      limits:
        memory: 1024M
```

### 시나리오 3: 데이터베이스 연결 고갈

**증상:**
- `connection pool exhausted` 에러
- Django 응답 시간 급증

**해결 방법:**

1. **DB 연결 풀 크기 증가** (config/settings.py)
```python
DATABASES = {
    'default': {
        # ... 기존 설정 ...
        'CONN_MAX_AGE': 60,  # 연결 재사용 (초)
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30초 타임아웃
        }
    }
}
```

2. **Gunicorn 워커 수 조정** (docker-compose.prod.yml)
```yaml
backend:
  command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --max-requests 1000 --max-requests-jitter 50
```

---

## 📈 권장 모니터링 주기

| 메트릭 | 확인 주기 | 알림 임계값 |
|--------|----------|------------|
| CPU 사용량 | 실시간 | 80% 이상 2분 지속 |
| 메모리 사용량 | 실시간 | 80% 이상 5분 지속 |
| Celery 작업 실패율 | 5분 | 10% 이상 |
| 슬로우 쿼리 | 5분 | 5분간 50개 이상 |
| API 응답 시간 | 실시간 | 95th percentile > 2초 |
| 디스크 사용량 | 1시간 | 85% 이상 |

---

## 🚀 배포 후 확인 사항

1. **의존성 설치**
```bash
pip install -r requirements.txt
```

2. **Docker 이미지 재빌드**
```bash
docker build -t hhyuninu/2025_techeer_team_i:latest .
docker push hhyuninu/2025_techeer_team_i:latest
```

3. **서버에서 재배포**
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

4. **메트릭 확인**
```bash
# Django 메트릭 확인
curl http://localhost:8000/metrics

# RabbitMQ 메트릭 확인
curl http://localhost:15692/metrics
```

5. **Grafana Cloud에서 데이터 수신 확인**
- Explore → Prometheus 데이터소스 선택
- 쿼리: `celery_tasks_total`
- 최근 5분간 데이터가 있는지 확인

---

## 📚 추가 리소스

- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [Django Prometheus Documentation](https://github.com/korfuri/django-prometheus)
- [Celery Monitoring](https://docs.celeryproject.org/en/stable/userguide/monitoring.html)
