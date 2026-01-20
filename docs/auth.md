# 🔐 인증 시스템 가이드

사용자 인증 및 권한 관리를 위한 API들을 설명합니다.

## 📋 개요

Backend 프로젝트는 JWT(JSON Web Token) 기반의 인증 시스템을 사용합니다.

- **라이브러리**: `djangorestframework-simplejwt`
- **토큰 유형**: Access Token + Refresh Token
- **토큰 만료**: Access(5분), Refresh(7일)

## 🔗 API 엔드포인트

### 1. 회원가입
**`POST /api/v1/auth/users/`**

새로운 사용자를 등록합니다.

#### 요청 본문
```json
{
  "email": "user@example.com",
  "password": "Password123!",
  "password_confirm": "Password123!",
  "nickname": "사용자닉네임"
}
```

#### 유효성 검증 규칙
- **이메일**: 형식 검증 + 중복 불가
- **비밀번호**: 8-16자 + 영문자/숫자/특수기호 각 1개 이상
- **닉네임**: 필수 입력 (2-20자)

#### 성공 응답 (201)
```json
{
  "message": "회원가입 성공",
  "user_id": 1,
  "email": "user@example.com",
  "nickname": "사용자닉네임"
}
```

#### 에러 응답 (400)
```json
{
  "email": ["이메일 형식이 올바르지 않습니다"],
  "password": ["문자/숫자/특수기호가 부족해요: 숫자, 특수기호"],
  "password_confirm": ["비밀번호가 일치하지 않습니다"]
}
```

### 2. 로그인
**`POST /api/v1/auth/tokens/`**

이메일/비밀번호 검증 후 JWT 토큰을 발급합니다.

#### 요청 본문
```json
{
  "email": "user@example.com",
  "password": "Password123!"
}
```

#### 성공 응답 (200)
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": 1,
  "email": "user@example.com",
  "nickname": "사용자닉네임"
}
```

#### 에러 응답 (401)
```json
{
  "error": "이메일 또는 비밀번호가 올바르지 않습니다."
}
```

### 3. 토큰 갱신
**`POST /api/v1/auth/refresh/`**

Refresh Token을 사용하여 새로운 Access Token을 발급합니다.

#### 요청 본문
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 성공 응답 (200)
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## 🔧 인증 방식

### 헤더 설정
API 요청 시 `Authorization` 헤더에 Access Token을 포함하세요:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Python 예제
```python
import requests

# 토큰 저장 (로그인 후)
access_token = "your_access_token_here"

# 인증이 필요한 API 호출
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.example.com/api/v1/some-endpoint/", headers=headers)
```

### JavaScript 예제
```javascript
// 토큰 저장 (로그인 후)
const accessToken = "your_access_token_here";

// 인증이 필요한 API 호출
const response = await fetch('/api/v1/some-endpoint/', {
    method: 'GET',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
    }
});
```

## ⚠️ 주의사항

### 토큰 만료 처리
- **Access Token**: 5분 후 만료 → Refresh Token으로 재발급
- **Refresh Token**: 7일 후 만료 → 재로그인 필요

### 보안 권장사항
- 토큰은 클라이언트 측에서 안전하게 저장하세요 (HttpOnly 쿠키 권장)
- API 호출 시 HTTPS 사용 필수
- 토큰 유출 시 즉시 로그아웃 처리

### 에러 처리
```javascript
// 401 Unauthorized 응답 처리
if (response.status === 401) {
    // 토큰 갱신 시도
    const refreshResponse = await fetch('/api/v1/auth/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: storedRefreshToken })
    });

    if (refreshResponse.ok) {
        const data = await refreshResponse.json();
        // 새 Access Token 저장
        accessToken = data.access;
        // 원래 요청 재시도
        return makeAuthenticatedRequest();
    } else {
        // Refresh Token도 만료됨 - 재로그인 필요
        redirectToLogin();
    }
}
```

## 🔍 관련 파일

- `music/views/auth.py` - 인증 API 구현
- `music/serializers/auth.py` - 인증 시리얼라이저
- `music/models.py` - User 모델