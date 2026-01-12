#!/usr/bin/env python
"""
Music API 테스트 스크립트
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def print_response(title, response):
    """응답 출력"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
    else:
        print(f"Error: {response.text}")
    print()

# 1. 음악 목록 조회
print("🧪 테스트 1: 음악 목록 조회")
r = requests.get(f"{BASE_URL}/db/tracks/")
print_response("음악 목록 (첫 페이지)", r)

# 2. 음악 상세 조회 (첫 번째 음악)
if r.status_code == 200:
    data = r.json()
    if data.get('results'):
        first_music_id = data['results'][0]['music_id']
        print(f"🧪 테스트 2: 음악 상세 조회 (ID: {first_music_id})")
        r2 = requests.get(f"{BASE_URL}/db/tracks/{first_music_id}/")
        print_response("음악 상세 정보", r2)

# 3. 검색 테스트
print("🧪 테스트 3: 검색 (search=아이유)")
r3 = requests.get(f"{BASE_URL}/db/tracks/?search=아이유")
print_response("검색 결과", r3)

# 4. 장르 필터링
print("🧪 테스트 4: 장르 필터링 (genre=팝)")
r4 = requests.get(f"{BASE_URL}/db/tracks/?genre=팝")
print_response("장르 필터링 결과", r4)

# 5. 태그 검색
print("🧪 테스트 5: 태그 검색")
r5 = requests.get(f"{BASE_URL}/tracks/search/tags?tags=신나는")
print_response("태그 검색 결과", r5)

print("\n✅ 모든 테스트 완료!")
