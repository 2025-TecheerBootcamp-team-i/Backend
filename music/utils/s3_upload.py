"""
S3 파일 업로드 유틸리티
Suno API에서 받은 MP3 파일을 S3에 업로드합니다.
"""
import os
import requests
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.utils import timezone


def download_file_from_url(url: str, timeout: int = 30) -> bytes:
    """
    URL에서 파일을 다운로드합니다.
    
    Args:
        url: 다운로드할 파일의 URL
        timeout: 요청 타임아웃 (초)
    
    Returns:
        파일 내용 (bytes)
    
    Raises:
        requests.RequestException: 다운로드 실패 시
    """
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()
    return response.content


def upload_to_s3(file_content: bytes, file_name: str, content_type: str = 'audio/mpeg') -> str:
    """
    파일을 S3에 업로드합니다.
    
    Args:
        file_content: 파일 내용 (bytes)
        file_name: S3에 저장할 파일명
        content_type: 파일의 MIME 타입
    
    Returns:
        S3 파일 URL
    
    Raises:
        ClientError: S3 업로드 실패 시
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    
    # S3 키 생성 (media/music/{timestamp}_{filename} 형식)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거
    safe_file_name = file_name.replace(' ', '_').replace('/', '_')
    s3_key = f'media/music/{timestamp}_{safe_file_name}'
    
    # S3에 업로드
    s3_client.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=s3_key,
        Body=file_content,
        ContentType=content_type,
        ACL='public-read'  # 공개 읽기 권한
    )
    
    # S3 URL 생성
    s3_url = f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/{s3_key}'
    return s3_url


def download_and_upload_to_s3(url: str, file_name: str = None) -> str:
    """
    URL에서 파일을 다운로드하고 S3에 업로드합니다.
    
    Args:
        url: 다운로드할 파일의 URL
        file_name: S3에 저장할 파일명 (없으면 URL에서 추출)
    
    Returns:
        S3 파일 URL
    
    Raises:
        Exception: 다운로드 또는 업로드 실패 시
    """
    try:
        # 파일명이 없으면 URL에서 추출
        if not file_name:
            file_name = url.split('/')[-1].split('?')[0]  # 쿼리 파라미터 제거
            if not file_name or '.' not in file_name:
                file_name = f'music_{int(timezone.now().timestamp())}.mp3'
        
        # URL에서 파일 다운로드
        print(f"[S3 Upload] 다운로드 중: {url}")
        file_content = download_file_from_url(url)
        print(f"[S3 Upload] 다운로드 완료: {len(file_content)} bytes")
        
        # S3에 업로드
        print(f"[S3 Upload] S3 업로드 중: {file_name}")
        s3_url = upload_to_s3(file_content, file_name)
        print(f"[S3 Upload] S3 업로드 완료: {s3_url}")
        
        return s3_url
    
    except Exception as e:
        print(f"[S3 Upload] 오류 발생: {str(e)}")
        raise
