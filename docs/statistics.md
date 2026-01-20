# 📈 사용자 통계 시스템 가이드

사용자의 음악 청취 패턴과 활동을 분석하는 통계 기능을 설명합니다.

## 📋 개요

사용자 통계 시스템은 다음과 같은 특징을 가집니다:

- **청취 시간 분석**: 총 청취 시간, 기간별 비교
- **선호도 분석**: Top 장르, 아티스트, 태그
- **활동 분석**: 재생 횟수, AI 생성 활동
- **기간 필터링**: 이번 달/전체 기간 선택

## 🔗 API 엔드포인트

### 1. 전체 통계 조회
**`GET /api/v1/statistics/`**

사용자의 전체 음악 통계를 종합적으로 조회합니다.

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `period` | string | ❌ | `month` (이번 달) / `all` (전체) - 기본값: `month` |

#### 응답 형식

```json
{
  "listening_time": {
    "total_seconds": 442800,
    "total_hours": 123.0,
    "play_count": 1500,
    "previous_period_hours": 110.0,
    "change_percent": 11.8
  },
  "top_genres": [
    {
      "rank": 1,
      "genre": "Indie",
      "play_count": 500,
      "percentage": 33.3
    }
  ],
  "top_artists": [
    {
      "rank": 1,
      "artist_id": 1,
      "artist_name": "아이유",
      "play_count": 300,
      "percentage": 20.0,
      "artist_image": "https://...",
      "image_large_circle": "https://..."
    }
  ],
  "top_tags": [
    {
      "tag_id": 1,
      "tag_key": "새벽감성",
      "play_count": 200,
      "percentage": 13.3
    }
  ],
  "ai_generation": {
    "total_generated": 3,
    "last_generated_at": "2026-01-14T10:30:00Z",
    "last_generated_days_ago": 2
  }
}
```

### 2. 청취 시간 통계
**`GET /api/v1/statistics/listening-time/`**

청취 시간 관련 세부 통계를 조회합니다.

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `period` | string | ❌ | `month` (이번 달) / `all` (전체) - 기본값: `month` |

#### 응답 형식

```json
{
  "total_seconds": 442800,
  "total_hours": 123.0,
  "play_count": 1500,
  "previous_period_hours": 110.0,
  "change_percent": 11.8,
  "daily_average": 4.1,
  "most_active_day": "Friday",
  "most_active_hour": 18
}
```

### 3. 선호 장르 통계
**`GET /api/v1/statistics/top-genres/`**

가장 많이 들은 장르 순위를 조회합니다.

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `period` | string | ❌ | `month` (이번 달) / `all` (전체) - 기본값: `month` |
| `limit` | integer | ❌ | 반환할 장르 수 - 기본값: 10 |

#### 응답 형식

```json
[
  {
    "rank": 1,
    "genre": "Indie",
    "play_count": 500,
    "percentage": 33.3
  },
  {
    "rank": 2,
    "genre": "Pop",
    "play_count": 300,
    "percentage": 20.0
  }
]
```

### 4. 선호 아티스트 통계
**`GET /api/v1/statistics/top-artists/`**

가장 많이 들은 아티스트 순위를 조회합니다.

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `period` | string | ❌ | `month` (이번 달) / `all` (전체) - 기본값: `month` |
| `limit` | integer | ❌ | 반환할 아티스트 수 - 기본값: 10 |

#### 응답 형식

```json
[
  {
    "rank": 1,
    "artist_id": 1,
    "artist_name": "아이유",
    "play_count": 300,
    "percentage": 20.0,
    "artist_image": "https://...",
    "image_large_circle": "https://...",
    "image_small_circle": "https://...",
    "image_square": "https://..."
  }
]
```

### 5. 선호 태그 통계
**`GET /api/v1/statistics/top-tags/`**

가장 많이 사용된 태그 순위를 조회합니다.

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `period` | string | ❌ | `month` (이번 달) / `all` (전체) - 기본값: `month` |
| `limit` | integer | ❌ | 반환할 태그 수 - 기본값: 10 |

#### 응답 형식

```json
[
  {
    "tag_id": 1,
    "tag_key": "새벽감성",
    "play_count": 200,
    "percentage": 13.3
  }
]
```

### 6. AI 생성 통계
**`GET /api/v1/statistics/ai-generation/`**

AI 음악 생성 활동 통계를 조회합니다.

#### 응답 형식

```json
{
  "total_generated": 3,
  "last_generated_at": "2026-01-14T10:30:00Z",
  "last_generated_days_ago": 2,
  "generated_this_month": 1,
  "most_used_genre": "Pop",
  "average_generation_time": 45.2
}
```

## 📊 통계 계산 방식

### 청취 시간 계산
```python
# 총 청취 시간 (초 단위)
total_seconds = sum(
    play_log.music.duration for play_log in user_play_logs
)

# 시간 단위 변환
total_hours = total_seconds / 3600

# 기간별 비교
if period == 'month':
    current_period = this_month_logs
    previous_period = last_month_logs
else:
    current_period = all_logs
    previous_period = None

change_percent = calculate_percentage_change(
    current_period.total_hours,
    previous_period.total_hours
)
```

### 선호도 분석
```python
# 장르 선호도
genre_stats = user_play_logs.values('music__genre') \
    .annotate(play_count=Count('id')) \
    .order_by('-play_count')

# 백분율 계산
total_plays = sum(stat['play_count'] for stat in genre_stats)
for stat in genre_stats:
    stat['percentage'] = (stat['play_count'] / total_plays) * 100
```

### AI 생성 활동
```python
# AI 생성곡 수
ai_generated_count = Music.objects.filter(
    user=user,
    is_ai=True
).count()

# 최근 생성 일자
last_generated = Music.objects.filter(
    user=user,
    is_ai=True
).aggregate(last_created=Max('created_at'))['last_created']
```

## 📅 기간 필터링

### 이번 달 (`period=month`)
- 현재 달의 1일부터 오늘까지의 데이터
- 이전 달과 비교하여 증감율 계산

### 전체 기간 (`period=all`)
- 사용자 가입일부터 오늘까지의 모든 데이터
- 장기적인 청취 패턴 분석

## 📈 데이터 시각화

### 추천 차트 타입

#### 청취 시간 추이
- **차트**: 선 그래프 (Line Chart)
- **X축**: 날짜/시간
- **Y축**: 청취 시간 (시간)
- **용도**: 일일/주간 청취 패턴 분석

#### 장르 분포
- **차트**: 원형 그래프 (Pie Chart) 또는 막대 그래프 (Bar Chart)
- **데이터**: 장르별 재생 횟수 및 백분율
- **용도**: 음악 취향 시각화

#### 아티스트 순위
- **차트**: 가로 막대 그래프 (Horizontal Bar Chart)
- **데이터**: 아티스트별 재생 횟수
- **용도**: Top 아티스트 목록 표시

#### 활동 시간대
- **차트**: 히트맵 (Heatmap)
- **X축**: 요일
- **Y축**: 시간대
- **용도**: 청취 활동 패턴 분석

## 📝 사용 예시

### 전체 통계 조회

```python
import requests

# 헤더 설정 (JWT 토큰 필요)
headers = {
    'Authorization': 'Bearer your_jwt_token',
    'Content-Type': 'application/json'
}

# 이번 달 통계 조회
response = requests.get(
    'https://api.example.com/api/v1/statistics/',
    params={'period': 'month'},
    headers=headers
)

data = response.json()

# 청취 시간 출력
listening_time = data['listening_time']
print(f"총 청취 시간: {listening_time['total_hours']:.1f}시간")
print(f"전월 대비: {listening_time['change_percent']:+.1f}%")

# Top 장르 출력
top_genres = data['top_genres'][:3]
for genre in top_genres:
    print(f"{genre['rank']}위: {genre['genre']} ({genre['percentage']}%)")
```

### JavaScript 예시

```javascript
// 통계 데이터 조회 및 차트 표시
const loadUserStatistics = async (period = 'month') => {
    try {
        const response = await fetch(`/api/v1/statistics/?period=${period}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        // 청취 시간 표시
        displayListeningTime(data.listening_time);

        // 장르 분포 차트
        createGenreChart(data.top_genres);

        // 아티스트 순위
        displayTopArtists(data.top_artists);

    } catch (error) {
        console.error('통계 조회 실패:', error);
    }
};

// 청취 시간 표시
const displayListeningTime = (listeningTime) => {
    const hours = listeningTime.total_hours.toFixed(1);
    const change = listeningTime.change_percent.toFixed(1);

    document.getElementById('total-hours').textContent = `${hours}시간`;
    document.getElementById('change-percent').textContent =
        `${change > 0 ? '+' : ''}${change}%`;
};
```

## ⚠️ 주의사항

### 데이터 정확성
- 재생 기록이 충분하지 않은 사용자는 의미 있는 통계가 부족할 수 있음
- 새로 가입한 사용자는 이전 기간 데이터가 없어 비교 불가능

### 성능 고려사항
- 대량의 재생 기록을 가진 사용자의 경우 집계 쿼리 최적화 필요
- 캐싱 전략을 통해 API 응답 속도 개선

### 프라이버시
- 통계 데이터는 사용자 개인 정보이므로 적절한 권한 제어 필요
- 민감한 데이터 노출 방지

## 🔍 관련 파일

- `music/views/statistics.py` - 통계 API 구현
- `music/services/internal/user_statistics.py` - 통계 계산 서비스
- `music/serializers/statistics.py` - 통계 데이터 시리얼라이저
- `music/models.py` - PlayLogs, Music 모델