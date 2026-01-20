# 📊 차트 시스템 가이드

실시간, 일간, AI 차트 조회 및 관리 기능을 설명합니다.

## 📋 개요

차트 시스템은 다음과 같은 특징을 가집니다:

- **실시간 차트**: 10분마다 갱신, 최근 3시간 재생 데이터 집계
- **일간 차트**: 매일 자정 갱신, 전날 전체 재생 데이터 집계
- **AI 차트**: 매일 자정 갱신, AI 생성곡만 집계
- **순위 변동**: 이전 차트와 비교하여 상승/하락 표시

## 🔗 API 엔드포인트

### 차트 조회
**`GET /api/v1/charts/{type}`**

지정된 타입의 최신 차트를 조회합니다.

#### 경로 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `type` | string | ✅ | 차트 타입 (`realtime` / `daily` / `ai`) |

#### 차트 타입 설명

| 타입 | 갱신 주기 | 집계 기간 | 설명 |
|------|-----------|-----------|------|
| `realtime` | 10분 | 최근 3시간 | 실시간 인기 차트 |
| `daily` | 매일 자정 | 전날 전체 | 일간 인기 차트 |
| `ai` | 매일 자정 | 전날 AI 곡만 | AI 생성곡 전용 차트 |

#### 응답 형식

```json
{
  "type": "realtime",
  "generated_at": "2026-01-20T15:30:00Z",
  "total_count": 100,
  "items": [
    {
      "rank": 1,
      "previous_rank": 2,
      "rank_change": 1,
      "play_count": 1500,
      "music": {
        "music_id": 123,
        "music_name": "인기곡 1",
        "artist": {
          "artist_id": 456,
          "artist_name": "아티스트1",
          "artist_image": "https://...",
          "image_large_circle": "https://...",
          "image_small_circle": "https://...",
          "image_square": "https://..."
        },
        "album": {
          "album_id": 789,
          "album_name": "앨범1",
          "album_image": "https://...",
          "image_square": "https://..."
        },
        "genre": "Pop",
        "duration": 210000,
        "is_ai": false,
        "audio_url": "https://...",
        "itunes_id": 123456789
      }
    }
  ]
}
```

#### 응답 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `type` | string | 차트 타입 |
| `generated_at` | datetime | 차트 생성 시각 |
| `total_count` | integer | 전체 항목 수 (최대 100) |
| `items[].rank` | integer | 현재 순위 |
| `items[].previous_rank` | integer | 이전 순위 |
| `items[].rank_change` | integer | 순위 변동 (양수: 상승, 음수: 하락) |
| `items[].play_count` | integer | 재생 횟수 |
| `items[].music` | object | 음악 상세 정보 |

## 🔄 차트 갱신 주기

### 실시간 차트 (`realtime`)
- **갱신 빈도**: 10분마다
- **집계 기간**: 최근 3시간
- **데이터 유지**: 7일
- **특징**: 가장 최신 트렌드 반영

### 일간 차트 (`daily`)
- **갱신 시각**: 매일 00:00 (자정)
- **집계 기간**: 전날 00:00 ~ 23:59
- **특징**: 일간 인기곡 순위

### AI 차트 (`ai`)
- **갱신 시각**: 매일 00:00 (자정)
- **집계 기간**: 전날 AI 생성곡만
- **특징**: AI 음악의 인기도 측정

## 📊 순위 변동 계산

### 계산 방식
```
rank_change = previous_rank - current_rank
```

### 예시
- 이전 2위 → 현재 1위: `rank_change = 2 - 1 = +1` (상승)
- 이전 1위 → 현재 3위: `rank_change = 1 - 3 = -2` (하락)
- 순위 유지: `rank_change = 0`

### 표시 방식
- `+1`: 1위 상승
- `-2`: 2위 하락
- `0`: 순위 유지
- `new`: 신규 진입
- `-`: 이전 차트 없음

## 📈 재생 데이터 집계

### 데이터 소스
- `play_logs` 테이블에서 재생 기록 수집
- 각 음악의 재생 횟수 집계

### 집계 로직
```sql
-- 실시간 차트 (최근 3시간)
SELECT music_id, COUNT(*) as play_count
FROM play_logs
WHERE played_at >= NOW() - INTERVAL '3 hours'
GROUP BY music_id
ORDER BY play_count DESC
LIMIT 100;

-- 일간 차트 (전날)
SELECT music_id, COUNT(*) as play_count
FROM play_logs
WHERE DATE(played_at) = CURRENT_DATE - 1
GROUP BY music_id
ORDER BY play_count DESC
LIMIT 100;
```

### AI 차트 필터링
```sql
-- AI 차트 (전날 AI 곡만)
SELECT music_id, COUNT(*) as play_count
FROM play_logs pl
JOIN music m ON pl.music_id = m.music_id
WHERE DATE(pl.played_at) = CURRENT_DATE - 1
  AND m.is_ai = true
GROUP BY music_id
ORDER BY play_count DESC
LIMIT 100;
```

## 🎯 사용 예시

### 실시간 차트 조회

```python
import requests

# 실시간 차트 조회
response = requests.get('https://api.example.com/api/v1/charts/realtime')
data = response.json()

print(f"차트 타입: {data['type']}")
print(f"생성 시각: {data['generated_at']}")
print(f"총 항목 수: {data['total_count']}")

# 상위 5곡 출력
for item in data['items'][:5]:
    music = item['music']
    print(f"{item['rank']}위: {music['music_name']} - {music['artist']['artist_name']}")
    print(f"  재생 횟수: {item['play_count']}, 순위 변동: {item['rank_change']}")
```

### JavaScript 예시

```javascript
// 차트 조회 함수
const fetchChart = async (type) => {
    try {
        const response = await fetch(`/api/v1/charts/${type}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(`차트 조회 실패: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('차트 조회 에러:', error);
        throw error;
    }
};

// 사용 예시
const realtimeChart = await fetchChart('realtime');
const dailyChart = await fetchChart('daily');
const aiChart = await fetchChart('ai');

// 차트 표시
const displayChart = (chartData) => {
    const chartList = document.getElementById('chart-list');

    chartData.items.forEach(item => {
        const listItem = document.createElement('li');

        const rankChange = item.rank_change > 0 ? `↑${item.rank_change}` :
                          item.rank_change < 0 ? `↓${Math.abs(item.rank_change)}` :
                          '−';

        listItem.innerHTML = `
            <span class="rank">${item.rank}</span>
            <span class="change">${rankChange}</span>
            <span class="title">${item.music.music_name}</span>
            <span class="artist">${item.music.artist.artist_name}</span>
            <span class="plays">${item.play_count}회</span>
        `;

        chartList.appendChild(listItem);
    });
};
```

## ⚠️ 주의사항

### 차트 갱신 타이밍
- 실시간 차트는 10분 단위로 갱신되므로 실시간 데이터가 아님
- 자정 직후에는 전날 차트가 표시될 수 있음

### 데이터 신뢰성
- 재생 기록이 적은 곡은 순위 변동이 크게 나타날 수 있음
- 신규 곡은 이전 차트 데이터가 없어 순위 변동 표시 안됨

### 성능 고려사항
- 차트 데이터는 캐싱되어 빠른 응답 가능
- 대량 트래픽 시에도 안정적인 응답 보장

## 🔧 백엔드 구현

### 차트 생성 태스크
```python
# Celery Beat 스케줄 설정 (settings.py)
CELERY_BEAT_SCHEDULE = {
    'generate-realtime-chart': {
        'task': 'music.tasks.charts.generate_realtime_chart',
        'schedule': crontab(minute='*/10'),  # 10분마다
    },
    'generate-daily-chart': {
        'task': 'music.tasks.charts.generate_daily_chart',
        'schedule': crontab(hour=0, minute=0),  # 매일 자정
    },
    'generate-ai-chart': {
        'task': 'music.tasks.charts.generate_ai_chart',
        'schedule': crontab(hour=0, minute=0),  # 매일 자정
    },
}
```

### 차트 데이터 저장
```python
# Charts 모델에 저장
chart = Charts.objects.create(
    music=music,
    play_count=play_count,
    chart_date=timezone.now().date(),
    rank=rank,
    type=chart_type
)
```

## 🔍 관련 파일

- `music/views/charts.py` - 차트 조회 API
- `music/tasks/charts.py` - 차트 생성 태스크
- `music/models.py` - Charts 모델
- `music/serializers/charts.py` - 차트 시리얼라이저