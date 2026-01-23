#!/bin/bash

# CPU 스파이크 디버깅 스크립트
# 사용법: ./monitoring/debug_cpu_spike.sh

echo "========================================="
echo "CPU 사용량 상위 프로세스 (컨테이너 내부)"
echo "========================================="

# 각 컨테이너의 CPU 사용량 확인
for container in backend celery celery-beat rabbitmq; do
    echo ""
    echo "[$container 컨테이너]"
    docker exec $container ps aux --sort=-%cpu | head -n 10
done

echo ""
echo "========================================="
echo "실행 중인 Celery 작업"
echo "========================================="
docker exec celery celery -A config inspect active 2>/dev/null || echo "Celery 작업 조회 실패"

echo ""
echo "========================================="
echo "최근 로그 (에러만)"
echo "========================================="

echo ""
echo "[Backend 로그]"
docker logs backend --tail 50 2>&1 | grep -i "error\|warning\|exception" | tail -n 10

echo ""
echo "[Celery 로그]"
docker logs celery --tail 50 2>&1 | grep -i "error\|warning\|exception" | tail -n 10

echo ""
echo "========================================="
echo "데이터베이스 연결 수"
echo "========================================="
docker exec backend python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT count(*) FROM pg_stat_activity')
    print(f'활성 DB 연결: {cursor.fetchone()[0]}개')
    cursor.execute('SELECT count(*) FROM pg_stat_activity WHERE state = \'active\'')
    print(f'실행 중인 쿼리: {cursor.fetchone()[0]}개')
" 2>/dev/null || echo "DB 연결 정보 조회 실패"

echo ""
echo "========================================="
echo "컨테이너별 리소스 사용량"
echo "========================================="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

echo ""
echo "완료! Grafana Cloud에서 더 자세한 메트릭을 확인하세요."
