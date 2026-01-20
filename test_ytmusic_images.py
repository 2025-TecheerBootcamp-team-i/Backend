#!/usr/bin/env python3
"""
YouTube Music API 이미지 수집 테스트 스크립트
아티스트와 앨범 이미지 조회 및 다운로드를 테스트합니다.
"""

import os
import sys
import requests
import logging
from pathlib import Path

# Django 환경 설정
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from music.services.external.ytmusic import YTMusicService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_image(url: str, filename: str, folder: str = "test_images") -> bool:
    """
    이미지 URL에서 파일을 다운로드합니다.

    Args:
        url: 이미지 URL
        filename: 저장할 파일명
        folder: 저장 폴더명

    Returns:
        성공 여부
    """
    try:
        # 폴더 생성
        folder_path = Path(folder)
        folder_path.mkdir(exist_ok=True)

        filepath = folder_path / filename

        # 이미지 다운로드
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()

        # 파일 저장
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"이미지 다운로드 완료: {filepath}")
        return True

    except Exception as e:
        logger.error(f"이미지 다운로드 실패 ({filename}): {e}")
        return False


def test_artist_image(artist_name: str):
    """아티스트 이미지 테스트"""
    print(f"\n{'='*50}")
    print(f"[ARTIST] 아티스트 이미지 테스트: {artist_name}")
    print(f"{'='*50}")

    try:
        image_url = YTMusicService.fetch_artist_image(artist_name)

        if image_url:
            print(f"[SUCCESS] 이미지 URL 발견: {image_url}")

            # 이미지 다운로드 및 저장
            filename = f"artist_{artist_name.replace(' ', '_').replace('/', '_')}.jpg"
            if download_image(image_url, filename):
                print(f"[SAVE] 이미지 저장됨: test_images/{filename}")
            else:
                print("[ERROR] 이미지 다운로드 실패")
        else:
            print("[NOT_FOUND] 이미지를 찾을 수 없음")

    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")


def test_album_image(album_name: str, artist_name: str = None):
    """앨범 이미지 테스트"""
    print(f"\n{'='*50}")
    print(f"[ALBUM] 앨범 이미지 테스트: {album_name}")
    if artist_name:
        print(f"[ARTIST] 아티스트: {artist_name}")
    print(f"{'='*50}")

    try:
        image_url = YTMusicService.fetch_album_image(album_name, artist_name)

        if image_url:
            print(f"[SUCCESS] 이미지 URL 발견: {image_url}")

            # 이미지 다운로드 및 저장
            safe_album = album_name.replace(' ', '_').replace('/', '_')[:50]
            safe_artist = artist_name.replace(' ', '_').replace('/', '_')[:30] if artist_name else ""
            filename = f"album_{safe_artist}_{safe_album}.jpg" if artist_name else f"album_{safe_album}.jpg"

            if download_image(image_url, filename):
                print(f"[SAVE] 이미지 저장됨: test_images/{filename}")
            else:
                print("[ERROR] 이미지 다운로드 실패")
        else:
            print("[NOT_FOUND] 이미지를 찾을 수 없음")

    except Exception as e:
        print(f"[ERROR] 에러 발생: {e}")


def main():
    """메인 테스트 함수"""
    print("YouTube Music API 이미지 수집 테스트")
    print("=" * 60)

    # 테스트할 아티스트 목록 (한국/외국 아티스트)
    test_artists = [
        "BTS",          # 한국 아티스트
    ]

    # 테스트할 앨범 목록
    test_albums = [
        ("ARMAGEDDON", "AESPA"),
    ]

    print("\n[TEST] 아티스트 이미지 테스트 시작...")
    for artist in test_artists:
        test_artist_image(artist)

    print("\n\n[TEST] 앨범 이미지 테스트 시작...")
    for album_name, artist_name in test_albums:
        test_album_image(album_name, artist_name)

    print(f"\n{'='*60}")
    print("[COMPLETE] 테스트 완료!")
    print("[INFO] test_images 폴더에서 다운로드된 이미지를 확인하세요.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()