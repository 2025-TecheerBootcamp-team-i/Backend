"""
S3 업로드 유틸리티 함수
"""
import requests
import boto3
from django.conf import settings
from django.utils import timezone
from botocore.exceptions import ClientError, BotoCoreError
import logging

logger = logging.getLogger(__name__)


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
    try:
        logger.info(f"[S3 업로드] 파일 다운로드 시작: {url}")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        file_content = response.content
        logger.info(f"[S3 업로드] 파일 다운로드 완료: {len(file_content)} bytes")
        return file_content
    except requests.RequestException as e:
        logger.error(f"[S3 업로드] 파일 다운로드 실패: {url}, 오류: {e}")
        raise


def upload_to_s3(file_content: bytes, file_name: str, content_type: str = 'audio/mpeg') -> str:
    """
    파일을 S3에 업로드합니다.
    
    Args:
        file_content: 업로드할 파일 내용 (bytes)
        file_name: 파일 이름 (확장자 포함)
        content_type: 파일 MIME 타입
        
    Returns:
        S3 URL (퍼블릭 접근 가능한 URL)
        
    Raises:
        ClientError: S3 업로드 실패 시
        ValueError: AWS 설정이 없을 때
    """
    # AWS 설정 확인
    if not settings.AWS_STORAGE_BUCKET_NAME:
        raise ValueError("AWS_STORAGE_BUCKET_NAME이 설정되지 않았습니다.")
    
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        raise ValueError("AWS_ACCESS_KEY_ID 또는 AWS_SECRET_ACCESS_KEY가 설정되지 않았습니다.")
    
    try:
        # S3 클라이언트 생성
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # S3 키 생성 (타임스탬프 + 파일명)
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        safe_file_name = file_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        s3_key = f'media/music/{timestamp}_{safe_file_name}'
        
        logger.info(f"[S3 업로드] S3 업로드 시작: bucket={settings.AWS_STORAGE_BUCKET_NAME}, key={s3_key}")
        
        # S3에 업로드 (ACL 없이 - 버킷 정책으로 퍼블릭 읽기 허용)
        s3_client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type
            # ACL은 사용하지 않음 (최신 S3 버킷은 ACL 비활성화)
            # 퍼블릭 읽기는 버킷 정책으로 설정해야 함
        )
        
        # S3 URL 생성
        if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN') and settings.AWS_S3_CUSTOM_DOMAIN:
            s3_url = f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/{s3_key}'
        else:
            s3_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}'
        
        logger.info(f"[S3 업로드] S3 업로드 완료: {s3_url}")
        return s3_url
        
    except (ClientError, BotoCoreError) as e:
        logger.error(f"[S3 업로드] S3 업로드 실패: {e}")
        raise
    except Exception as e:
        logger.error(f"[S3 업로드] 예상치 못한 오류: {e}")
        raise


def download_and_upload_to_s3(url: str, file_name: str = None, content_type: str = 'audio/mpeg') -> str:
    """
    URL에서 파일을 다운로드하고 S3에 업로드합니다.
    
    Args:
        url: 다운로드할 파일의 URL
        file_name: 저장할 파일 이름 (None이면 URL에서 추출)
        content_type: 파일 MIME 타입
        
    Returns:
        S3 URL
        
    Raises:
        requests.RequestException: 다운로드 실패 시
        ClientError: S3 업로드 실패 시
    """
    # 파일명이 없으면 URL에서 추출
    if not file_name:
        file_name = url.split('/')[-1].split('?')[0]  # 쿼리 파라미터 제거
        if not file_name or '.' not in file_name:
            file_name = f'audio_{timezone.now().strftime("%Y%m%d_%H%M%S")}.mp3'
    
    # 파일 다운로드
    file_content = download_file_from_url(url)
    
    # S3 업로드
    s3_url = upload_to_s3(file_content, file_name, content_type)
    
    return s3_url


def is_suno_url(url: str) -> bool:
    """
    URL이 Suno CDN URL인지 확인합니다.
    
    Args:
        url: 확인할 URL
        
    Returns:
        Suno URL이면 True, 아니면 False
    """
    if not url:
        return False
    
    # Suno가 사용하는 다양한 CDN 도메인
    suno_domains = [
        'cdn.suno.ai',
        'cdn1.suno.ai',
        'suno.ai',
        'sunoapi.org',
        'musicfile.api.box',  # Suno의 Box CDN
        'audiopipe.suno.ai'   # Suno의 Audio Pipe
    ]
    return any(domain in url for domain in suno_domains)


def is_s3_url(url: str) -> bool:
    """
    URL이 S3 URL인지 확인합니다.
    """
    if not url:
        return False
    
    # S3 도메인 패턴 체크
    if 's3.amazonaws.com' in url or '.s3.' in url:
        return True
        
    # 버킷 이름이 설정된 경우에만 체크
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    if bucket_name and bucket_name in url:
        return True
        
    return False


def upload_image_to_s3(
    image_url: str, 
    image_type: str, 
    entity_id: int, 
    entity_name: str = None
) -> str:
    """
    이미지 URL을 다운로드하여 S3에 업로드합니다.
    
    Lambda가 리사이징하도록 media/images/{type}/original/ 경로에 저장합니다.
    
    Args:
        image_url: 다운로드할 이미지 URL
        image_type: 이미지 타입 ('artists', 'albums')
        entity_id: 엔티티 ID (아티스트/앨범/트랙 ID)
        entity_name: 엔티티 이름 (파일명에 사용, 없으면 ID만 사용)
        
    Returns:
        S3 URL (원본 이미지 경로)
        
    Raises:
        requests.RequestException: 다운로드 실패 시
        ClientError: S3 업로드 실패 시
    """
    # AWS 설정 확인
    if not settings.AWS_STORAGE_BUCKET_NAME:
        raise ValueError("AWS_STORAGE_BUCKET_NAME이 설정되지 않았습니다.")
    
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        raise ValueError("AWS_ACCESS_KEY_ID 또는 AWS_SECRET_ACCESS_KEY가 설정되지 않았습니다.")
    
    try:
        # 이미지 다운로드 (Wikipedia 403 에러 방지를 위해 User-Agent 추가)
        logger.info(f"[S3 이미지] 다운로드 시작: {image_url[:80]}...")
        headers = {
            'User-Agent': 'MusicStreamingApp/1.0 (contact@musicapp.com)'
        }
        response = requests.get(image_url, timeout=30, headers=headers)
        response.raise_for_status()
        image_content = response.content
        logger.info(f"[S3 이미지] 다운로드 완료: {len(image_content)} bytes")
        
        # Content-Type 확인 및 확장자 결정
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        if 'png' in content_type:
            extension = 'png'
        elif 'gif' in content_type:
            extension = 'gif'
        elif 'webp' in content_type:
            extension = 'webp'
        else:
            extension = 'jpg'
        
        # 파일명 생성 (안전한 문자만 사용)
        safe_name = ''
        if entity_name:
            # 특수문자 제거 및 공백을 언더스코어로 변환
            safe_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in entity_name)
            safe_name = f"_{safe_name[:50]}"  # 최대 50자
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"{entity_id}{safe_name}_{timestamp}.{extension}"
        
        # S3 키 생성 (Lambda 트리거 경로: media/images/{type}/original/)
        s3_key = f"media/images/{image_type}/original/{file_name}"
        
        # S3 클라이언트 생성
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        logger.info(f"[S3 이미지] 업로드 시작: bucket={settings.AWS_STORAGE_BUCKET_NAME}, key={s3_key}")
        
        # S3에 업로드
        s3_client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key,
            Body=image_content,
            ContentType=content_type,
            CacheControl='max-age=31536000'  # 1년 캐시
        )
        
        # S3 URL 생성 헬퍼 함수
        def get_s3_url(key: str) -> str:
            if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN') and settings.AWS_S3_CUSTOM_DOMAIN:
                return f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/{key}'
            else:
                return f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}'
        
        original_url = get_s3_url(s3_key)
        logger.info(f"[S3 이미지] 업로드 완료: {original_url}")
        
        # Celery 태스크로 이미지 리사이징 시작 (Lambda 대신)
        try:
            from music.tasks.image_resize import resize_image_task
            resize_image_task.delay(s3_key, image_type, entity_id)
            logger.info(f"[S3 이미지] 리사이징 태스크 시작: {s3_key}, entity_id={entity_id}")
        except Exception as e:
            logger.warning(f"[S3 이미지] 리사이징 태스크 시작 실패 (계속 진행): {e}")
        
        # 리사이징된 이미지 URL 생성 (예상 경로 - 실제 생성은 Celery 태스크에서)
        resized_urls = {}
        if image_type == 'artists':
            # 파일명에서 확장자 추출 및 변경
            filename_without_ext = file_name.rsplit('.', 1)[0]
            
            # 원형 이미지 URL (PNG)
            large_circle_key = f"media/images/artists/circular/228x228/{filename_without_ext}.png"
            small_circle_key = f"media/images/artists/circular/208x208/{filename_without_ext}.png"
            
            # 사각형 이미지 URL (JPEG)
            square_key = f"media/images/artists/square/220x220/{filename_without_ext}.jpg"
            
            resized_urls = {
                'original': original_url,
                'image_large_circle': get_s3_url(large_circle_key),
                'image_small_circle': get_s3_url(small_circle_key),
                'image_square': get_s3_url(square_key),
            }
        elif image_type == 'albums':
            # 파일명에서 확장자 추출 및 변경
            filename_without_ext = file_name.rsplit('.', 1)[0]
            
            # 사각형 이미지 URL (JPEG) - 220x220과 360x360
            square_220_key = f"media/images/albums/square/220x220/{filename_without_ext}.jpg"
            square_360_key = f"media/images/albums/square/360x360/{filename_without_ext}.jpg"
            
            resized_urls = {
                'original': original_url,
                'image_square': get_s3_url(square_220_key),
                'image_large_square': get_s3_url(square_360_key),
            }
        
        return resized_urls
        
    except requests.RequestException as e:
        logger.error(f"[S3 이미지] 다운로드 실패: {image_url}, 오류: {e}")
        raise
    except (ClientError, BotoCoreError) as e:
        logger.error(f"[S3 이미지] S3 업로드 실패: {e}")
        raise
    except Exception as e:
        logger.error(f"[S3 이미지] 예상치 못한 오류: {e}")
        raise
