# 📚 프로젝트 문서 (Documentation)

이 폴더는 Backend 프로젝트의 모든 문서들을 체계적으로 정리한 공간입니다.

## 📁 docs 폴더 구조

```
docs/
├── auth.md                      # 🔐 인증 시스템 가이드
├── search.md                    # 🔍 음악 검색 가이드
├── playlist.md                  # 📋 플레이리스트 관리 가이드
├── charts.md                    # 📊 차트 시스템 가이드
├── statistics.md                # 📈 사용자 통계 가이드
├── ai-music.md                  # 🎵 AI 음악 생성 가이드
├── deployment.md                # 🚀 배포 및 운영 가이드
├── FLOW_ARTIST_SEARCH_AND_TRACK_CLICK.md  # 아티스트 검색 → 곡 클릭 흐름 분석
├── TREE.md                      # 프로젝트 파일 구조 및 개발 진행 상황
└── .cursorrules                 # 프로젝트 개발 규칙 및 PRD
```

## 📖 문서 종류

### 📋 프로젝트 문서
- **[TREE.md](./TREE.md)** - 프로젝트 파일 구조 및 개발 진행 상황
- **[.cursorrules](./.cursorrules)** - 프로젝트 개발 규칙 및 PRD (Product Requirements Document)

### 🔧 기능별 매뉴얼
각 기능별로 상세한 API 가이드와 사용법을 제공합니다.

#### 🔐 [인증 시스템](./docs/auth.md)
- 회원가입/로그인 API
- JWT 토큰 관리
- 사용자 권한 처리

#### 🔍 [음악 검색](./docs/search.md)
- iTunes API 연동 검색
- 아티스트/앨범 자동 생성
- 이미지 자동 수집 및 리사이징

#### 📋 [플레이리스트 관리](./docs/playlist.md)
- 플레이리스트 CRUD
- 곡 추가/삭제
- 공유 및 좋아요 기능

#### 📊 [차트 시스템](./docs/charts.md)
- 실시간 차트
- 일간 차트
- AI 음악 전용 차트

#### 📈 [사용자 통계](./docs/statistics.md)
- 청취 시간 분석
- 선호 장르/아티스트/태그
- AI 생성 통계

#### 🎵 [AI 음악 생성](./docs/ai-music.md)
- LangChain + Suno API 연동
- 음악 생성 워크플로우
- 비동기 작업 관리

#### 🚀 [배포 및 운영](./docs/deployment.md)
- Docker 기반 배포
- 롤백 절차
- 모니터링 및 트러블슈팅

## 🎯 사용법

1. **개발 시작 전**: [docs/TREE.md](./docs/TREE.md)를 읽어서 프로젝트 구조를 파악하세요
2. **특정 기능 작업 시**: 해당 기능의 .md 파일을 확인하세요
3. **배포 관련**: [docs/deployment.md](./docs/deployment.md)를 참고하세요

## 📝 문서 작성 규칙

- 모든 API 엔드포인트는 실제 코드와 일치해야 합니다
- 예제 코드는 복사해서 사용할 수 있도록 실제 동작 가능한 형태로 작성
- 새로운 기능 추가 시 docs 폴더에 기능명.md 파일을 추가하세요

## 🔗 관련 링크

- [프로젝트 메인 README](../README.md) - 프로젝트 소개 및 설치 가이드
- [API 스키마](/api/schema/) - 자동 생성된 API 문서