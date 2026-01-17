# 이미지 리사이징 Lambda 함수

S3에 이미지가 업로드되면 자동으로 리사이징하는 AWS Lambda 함수입니다.

## 기능

### 이미지 타입별 리사이징

| 이미지 타입 | 원형 | 사각형 |
|------------|------|--------|
| 아티스트 (artists) | 228×228, 208×208 | 220×220 |
| 앨범 (albums) | - | 220×220 |
| 트랙 (tracks) | - | 48×48 |

### S3 저장 구조

```
media/images/
├── artists/
│   ├── original/           ← 원본 업로드 (Lambda 트리거)
│   ├── circular/
│   │   ├── 228x228/        ← Lambda 자동 생성
│   │   └── 208x208/        ← Lambda 자동 생성
│   └── square/220x220/     ← Lambda 자동 생성
│
├── albums/
│   ├── original/           ← 원본 업로드 (Lambda 트리거)
│   └── square/220x220/     ← Lambda 자동 생성
│
└── tracks/
    ├── original/           ← 원본 업로드 (Lambda 트리거)
    └── square/48x48/       ← Lambda 자동 생성
```

## 사전 준비

### 1. AWS CLI 설치 및 설정

```bash
# AWS CLI 설치 (macOS)
brew install awscli

# AWS 자격 증명 설정
aws configure
# AWS Access Key ID: [입력]
# AWS Secret Access Key: [입력]
# Default region name: ap-northeast-2
# Default output format: json
```

### 2. AWS SAM CLI 설치

```bash
# macOS
brew install aws-sam-cli

# 설치 확인
sam --version
```

## 배포

### 방법 1: 새 S3 버킷 생성하며 배포

```bash
# lambda 디렉토리로 이동
cd lambda

# 빌드
sam build

# 첫 배포 (대화형 설정)
sam deploy --guided

# 설정 예시:
# Stack Name: music-image-resizer
# AWS Region: ap-northeast-2
# Parameter S3BucketName: your-unique-bucket-name
# Confirm changes before deploy: y
# Allow SAM CLI IAM role creation: Y
# Disable rollback: N
# Save arguments to configuration file: Y
# SAM configuration file: samconfig.toml
# SAM configuration environment: default
```

### 방법 2: 기존 S3 버킷 사용

기존 S3 버킷을 사용하려면 `template-existing-bucket.yaml`을 사용하세요:

```bash
# 빌드
sam build --template template-existing-bucket.yaml

# 배포
sam deploy --guided --template template-existing-bucket.yaml

# Parameter ExistingBucketName에 기존 버킷 이름 입력
```

**주의**: 기존 버킷 사용 시 S3 이벤트 트리거를 AWS Console에서 수동으로 설정해야 합니다.

### 이후 배포 (변경사항 적용)

```bash
cd lambda
sam build
sam deploy
```

## 로컬 테스트

### 테스트 이벤트 생성

```bash
# 테스트 이벤트 파일 생성
cat > events/test-event.json << 'EOF'
{
  "Records": [
    {
      "s3": {
        "bucket": {
          "name": "your-bucket-name"
        },
        "object": {
          "key": "media/images/artists/original/test.jpg"
        }
      }
    }
  ]
}
EOF
```

### 로컬 실행

```bash
# 로컬 Lambda 실행 (Docker 필요)
sam local invoke ImageResizerFunction -e events/test-event.json
```

## 트러블슈팅

### 1. Pillow 설치 오류

Lambda는 Amazon Linux 2 환경입니다. Pillow가 제대로 빌드되지 않으면:

```bash
# Docker를 사용한 빌드 (권장)
sam build --use-container
```

### 2. 권한 오류

S3 버킷에 대한 읽기/쓰기 권한이 없으면 CloudWatch Logs에서 오류 확인:

```bash
# CloudWatch Logs 확인
aws logs tail /aws/lambda/music-image-resizer --follow
```

### 3. 무한 루프

리사이징된 이미지가 다시 Lambda를 트리거하면 무한 루프가 발생합니다.
이를 방지하기 위해 코드에서 `/original/` 경로만 처리합니다.

## 삭제

```bash
# 스택 삭제 (S3 버킷 포함)
sam delete --stack-name music-image-resizer

# S3 버킷이 비어있지 않으면 먼저 비우기
aws s3 rm s3://your-bucket-name --recursive
```

## 비용

- **Lambda**: 월 100만 요청 무료, 이후 $0.20/100만 요청
- **S3**: 저장 용량 및 요청 비용
- **예상 비용**: 월 1만 이미지 처리 시 약 $1 미만

## 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| BUCKET_NAME | S3 버킷 이름 | template에서 설정 |
