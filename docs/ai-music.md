# 🎵 AI 음악 생성 시스템 가이드

LangChain과 Suno API를 활용한 AI 음악 생성 기능을 설명합니다.

## 📋 개요

AI 음악 생성 시스템은 다음과 같은 특징을 가집니다:

- **프롬프트 기반 생성**: 자연어로 음악 스타일과 분위기를 지정
- **LangChain 통합**: 한국어 프롬프트를 영어로 변환하여 Suno API에 최적화
- **비동기 처리**: 음악 생성은 백그라운드에서 처리하여 UX 개선
- **다양한 옵션**: 보컬/반주 선택, 태그 자동 생성

## 🔗 API 엔드포인트

### 1. AI 음악 생성 (동기)
**`POST /api/v1/generate/`**

Suno API를 사용한 AI 음악 생성 (동기 처리).

#### 요청 본문
```json
{
  "prompt": "신나는 여름 댄스곡",
  "user_id": 1,
  "make_instrumental": false
}
```

#### 응답 형식 (성공)
```json
{
  "music_id": 123,
  "music_name": "Summer Dance Beat",
  "artist_name": "AI Artist",
  "album_name": "AI Generated",
  "audio_url": "https://...",
  "duration": 180000,
  "genre": "Electronic",
  "is_ai": true,
  "created_at": "2026-01-20T10:30:00Z"
}
```

#### 에러 응답
```json
// 크레딧 부족
{
  "error": "Suno API 크레딧이 부족합니다. 크레딧을 충전해주세요.",
  "details": "..."
}

// 인증 실패
{
  "error": "Suno API 인증에 실패했습니다. API 키를 확인해주세요.",
  "details": "..."
}
```

### 2. AI 음악 생성 (비동기)
**`POST /api/v1/generate-async/`**

Celery를 사용한 비동기 음악 생성.

#### 요청 본문
```json
{
  "prompt": "잔잔한 피아노 발라드",
  "user_id": 1,
  "make_instrumental": true
}
```

#### 응답 형식 (즉시 반환)
```json
{
  "task_id": "celery-task-id-123",
  "message": "음악 생성 작업이 시작되었습니다.",
  "status": "PENDING"
}
```

### 3. 작업 상태 조회
**`GET /api/v1/task/{task_id}/`**

Celery 작업 진행 상태 확인.

#### 응답 형식
```json
{
  "task_id": "celery-task-id-123",
  "status": "SUCCESS",
  "result": {
    "music_id": 456,
    "music_name": "Piano Ballad",
    // ... 음악 정보
  }
}
```

### 4. Suno 작업 상태 조회
**`GET /api/v1/suno-task/{task_id}/`**

Suno API의 실제 작업 상태 확인.

#### 응답 형식
```json
{
  "task_id": "suno-task-456",
  "status": "complete",
  "progress": 100,
  "result": {
    "id": "track-123",
    "title": "Generated Song",
    "audio_url": "https://...",
    "image_url": "https://...",
    "duration": 180
  }
}
```

## 🔄 생성 플로우

### 동기 생성 플로우
```
1. 프롬프트 입력 → LangChain 변환 → Suno API 호출
2. 음악 생성 완료 대기 (최대 2분)
3. DB 저장 및 응답 반환
```

### 비동기 생성 플로우
```
1. 프롬프트 입력 → Celery 태스크 생성 → 즉시 응답
2. 백그라운드에서 LangChain 변환 → Suno API 호출
3. 음악 생성 완료 → DB 저장 → 태스크 완료
4. 클라이언트에서 상태 폴링 또는 웹훅으로 완료 알림
```

## 🎼 프롬프트 작성 가이드

### 효과적인 프롬프트 예시
```javascript
// 좋은 예시
"신나는 여름 EDM, 일렉트로닉 댄스 뮤직, 120BPM"

// 더 구체적인 예시
"잔잔한 피아노 선율의 뉴에이지 음악, 평화로운 분위기"

// 스타일 + 무드 + 세부사항
"록 스타일의 강렬한 기타 리프, 반항적인 에너지, 140BPM"
```

### 피해야 할 프롬프트
```javascript
// 너무 추상적
"좋은 음악"

// 저작권 문제 유발 가능
"아이유 스타일의 노래"

// 기술적 용어 남용
"4/4박자, C메이저, 128BPM의 팝송"
```

## ⚙️ 생성 옵션

### make_instrumental
- `false` (기본값): 보컬 포함
- `true`: 반주만 생성

### 태그 자동 생성
음악 생성 시 자동으로 관련 태그가 생성됩니다:
- 장르 태그 (pop, rock, electronic 등)
- 무드 태그 (happy, sad, energetic 등)
- 계절/상황 태그 (summer, party, relaxation 등)

## 📊 생성 통계

사용자의 AI 음악 생성 활동을 통계로 확인할 수 있습니다:

```json
{
  "total_generated": 15,
  "last_generated_at": "2026-01-19T14:30:00Z",
  "last_generated_days_ago": 1,
  "generated_this_month": 8,
  "most_used_genre": "Pop",
  "average_generation_time": 85.3
}
```

## 🔧 기술 구현

### LangChain 통합
```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# 한국어 프롬프트 → 영어 최적화 프롬프트 변환
korean_prompt = "신나는 여름 노래"
english_prompt = langchain_chain.run(korean_prompt)
# 결과: "upbeat summer pop song with electronic beats"
```

### Suno API 연동
```python
# 음악 생성 요청
response = suno_api.generate({
    "prompt": optimized_prompt,
    "make_instrumental": False,
    "duration": 180
})

# 생성 상태 확인
status = suno_api.get_task_status(task_id)
```

### Celery 비동기 처리
```python
from celery import shared_task

@shared_task
def generate_music_task(user_prompt, user_id, make_instrumental):
    # LangChain 변환
    optimized_prompt = langchain_service.optimize_prompt(user_prompt)

    # Suno API 호출
    result = suno_service.generate_music(optimized_prompt, make_instrumental)

    # DB 저장
    music = Music.objects.create(
        user_id=user_id,
        music_name=result['title'],
        audio_url=result['audio_url'],
        is_ai=True
    )

    return music.id
```

## 📝 사용 예시

### 동기 생성
```python
import requests

# AI 음악 생성
response = requests.post('https://api.example.com/api/v1/generate/', json={
    'prompt': '잔잔한 피아노 음악',
    'user_id': 1,
    'make_instrumental': True
})

if response.status_code == 201:
    music_data = response.json()
    print(f"생성된 음악: {music_data['music_name']}")
    # 바로 음악 재생 가능
```

### 비동기 생성 + 상태 모니터링
```javascript
// 1. 음악 생성 요청
const generateMusic = async (prompt) => {
    const response = await fetch('/api/v1/generate-async/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            prompt: prompt,
            user_id: currentUserId,
            make_instrumental: false
        })
    });

    const data = await response.json();
    return data.task_id;
};

// 2. 상태 확인
const checkTaskStatus = async (taskId) => {
    const response = await fetch(`/api/v1/task/${taskId}/`);
    const status = await response.json();

    if (status.status === 'SUCCESS') {
        // 음악 생성 완료
        const music = status.result;
        playMusic(music.audio_url);
    } else if (status.status === 'PENDING') {
        // 아직 진행 중
        setTimeout(() => checkTaskStatus(taskId), 5000);
    }
};

// 사용 예시
const taskId = await generateMusic('신나는 팝송');
checkTaskStatus(taskId);
```

## ⚠️ 주의사항

### 크레딧 관리
- Suno API는 유료 서비스이므로 크레딧 잔액을 모니터링해야 함
- 크레딧 부족 시 사용자에게 안내 필요

### 생성 시간
- 음악 생성은 1-3분 소요될 수 있음
- 비동기 처리로 사용자 경험 개선 권장

### 프롬프트 품질
- 구체적이고 명확한 프롬프트가 좋은 결과물 생성
- 너무 긴 프롬프트는 오히려 품질 저하 유발 가능

### 저작권 고려
- 생성된 음악은 AI 저작물로 취급
- 상업적 사용 시 별도 라이선스 확인 필요

## 🔍 관련 파일

- `music/views/ai_music.py` - AI 음악 생성 API
- `music/services/ai_music_service.py` - AI 음악 생성 서비스
- `music/music_generate/services.py` - LangChain, Suno API 서비스
- `music/tasks/ai_music.py` - 비동기 생성 태스크