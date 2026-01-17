#!/bin/bash

export PATH="/opt/homebrew/bin:$PATH"
# AWS credentials should be set via environment variables or AWS CLI configuration
# export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
# export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
export AWS_DEFAULT_REGION=ap-northeast-2

TARGET_ARTISTS=1541
TARGET_ALBUMS=6111
CHECK_INTERVAL=300  # 5분 = 300초
LOG_FILE="/tmp/image_upload_monitor.log"

log() {
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

check_upload_progress() {
    artists_count=$(aws s3 ls s3://music-streaming-audio/media/images/artists/original/ --recursive 2>/dev/null | wc -l | tr -d ' ')
    albums_count=$(aws s3 ls s3://music-streaming-audio/media/images/albums/original/ --recursive 2>/dev/null | wc -l | tr -d ' ')
    
    echo "$artists_count $albums_count"
}

restart_artist_migration() {
    log "🔄 아티스트 이미지 마이그레이션 재시작..."
    cd /Users/doo._.hyun/Backend
    docker exec backend-web-1 python manage.py migrate_images_to_s3 --type=artist > /dev/null 2>&1 &
}

log "🚀 이미지 업로드 모니터링 시작"

# 초기 상태 확인
prev_state=$(check_upload_progress)
prev_artists=$(echo $prev_state | cut -d' ' -f1)
prev_albums=$(echo $prev_state | cut -d' ' -f2)

log "초기 상태: 아티스트 $prev_artists / $TARGET_ARTISTS, 앨범 $prev_albums / $TARGET_ALBUMS"

# 완료 체크 함수
check_completion() {
    artists_count=$1
    albums_count=$2
    
    if [ "$artists_count" -ge "$TARGET_ARTISTS" ] && [ "$albums_count" -ge "$TARGET_ALBUMS" ]; then
        return 0  # 완료
    fi
    return 1  # 미완료
}

# 메인 루프
while true; do
    sleep $CHECK_INTERVAL
    
    # 현재 상태 확인
    current_state=$(check_upload_progress)
    current_artists=$(echo $current_state | cut -d' ' -f1)
    current_albums=$(echo $current_state | cut -d' ' -f2)
    
    artists_diff=$((current_artists - prev_artists))
    albums_diff=$((current_albums - prev_albums))
    
    artists_percent=$(echo "scale=1; $current_artists * 100 / $TARGET_ARTISTS" | bc 2>/dev/null || echo "0")
    albums_percent=$(echo "scale=1; $current_albums * 100 / $TARGET_ALBUMS" | bc 2>/dev/null || echo "0")
    
    log "📊 진행 상황:"
    log "   아티스트: $current_artists / $TARGET_ARTISTS ($artists_percent%) - 변화: $artists_diff"
    log "   앨범: $current_albums / $TARGET_ALBUMS ($albums_percent%) - 변화: $albums_diff"
    
    # 완료 체크
    if check_completion $current_artists $current_albums; then
        log "✅ 모든 업로드 완료! 모니터링 종료"
        break
    fi
    
    # 진행이 안 되고 있는지 체크 (아티스트만)
    if [ "$current_artists" -lt "$TARGET_ARTISTS" ]; then
        if [ "$artists_diff" -eq 0 ]; then
            log "⚠️  아티스트 업로드 진행이 없습니다. 재시작합니다..."
            restart_artist_migration
            sleep 10  # 재시작 후 잠시 대기
        else
            log "✅ 아티스트 업로드 진행 중 (+$artists_diff개)"
        fi
    fi
    
    # 이전 상태 업데이트
    prev_artists=$current_artists
    prev_albums=$current_albums
done
