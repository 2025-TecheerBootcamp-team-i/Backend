"""
이미지 리사이징 유틸리티

Lambda 함수를 Django 프로젝트로 포팅한 버전
S3에 업로드된 이미지를 자동으로 리사이징합니다.
- 아티스트 이미지: 원형 2개 (228x228, 208x208) + 사각형 1개 (220x220)
- 앨범 이미지: 사각형 2개 (220x220, 360x360)
- 트랙 이미지: 사각형 1개 (48x48)
"""
import boto3
from PIL import Image, ImageDraw
import io
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# 이미지 타입별 리사이징 설정
RESIZE_CONFIG = {
    'artists': {
        'circular': [(228, 228), (208, 208)],  # 원형 이미지
        'square': [(220, 220)]  # 사각형 이미지
    },
    'albums': {
        'circular': [],  # 원형 필요 없음
        'square': [(220, 220), (360, 360)]  # 사각형 이미지 (220x220, 360x360)
    },
    'tracks': {
        'circular': [],  # 원형 필요 없음
        'square': [(48, 48)]
    }
}


def get_s3_client():
    """S3 클라이언트 생성"""
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )


def get_s3_url(key: str) -> str:
    """S3 URL 생성"""
    if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN') and settings.AWS_S3_CUSTOM_DOMAIN:
        return f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/{key}'
    else:
        return f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}'


def is_image_file(key: str) -> bool:
    """이미지 파일인지 확인"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    return any(key.lower().endswith(ext) for ext in image_extensions)


def extract_image_type(key: str) -> str:
    """
    S3 키에서 이미지 타입 추출
    
    예: media/images/artists/original/xxx.jpg -> artists
    """
    parts = key.split('/')
    
    # media/images/{type}/original/ 구조에서 type 추출
    if 'images' in parts:
        images_idx = parts.index('images')
        if images_idx + 1 < len(parts):
            image_type = parts[images_idx + 1]
            if image_type in RESIZE_CONFIG:
                return image_type
    
    return None


def download_image_from_s3(s3_key: str) -> Image.Image:
    """S3에서 이미지 다운로드"""
    s3_client = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    response = s3_client.get_object(Bucket=bucket, Key=s3_key)
    image_data = response['Body'].read()
    return Image.open(io.BytesIO(image_data))


def create_circular_image(image: Image.Image, size: int) -> Image.Image:
    """
    이미지를 원형으로 변환합니다.
    
    Args:
        image: PIL Image 객체
        size: 원형 이미지 크기 (정사각형)
    
    Returns:
        원형 이미지 (PNG, 투명 배경)
    """
    # 원본 복사 (원본 변경 방지)
    img = image.copy()
    
    # 1. 정사각형으로 중앙 크롭
    width, height = img.size
    min_dimension = min(width, height)
    
    left = (width - min_dimension) // 2
    top = (height - min_dimension) // 2
    right = left + min_dimension
    bottom = top + min_dimension
    
    cropped = img.crop((left, top, right, bottom))
    
    # 2. 원하는 크기로 리사이징
    cropped = cropped.resize((size, size), Image.Resampling.LANCZOS)
    
    # 3. 원형 마스크 생성
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    # 4. 투명 배경 이미지 생성
    circular_image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # 5. 원본을 RGBA로 변환
    if cropped.mode != 'RGBA':
        cropped = cropped.convert('RGBA')
    
    # 6. 마스크 적용
    circular_image.paste(cropped, (0, 0), mask)
    
    return circular_image


def create_square_image(image: Image.Image, size: tuple) -> Image.Image:
    """
    이미지를 사각형으로 리사이징합니다.
    
    Args:
        image: PIL Image 객체
        size: (width, height) 튜플
    
    Returns:
        리사이징된 사각형 이미지
    """
    # 원본 복사
    img = image.copy()
    
    # 정사각형으로 중앙 크롭 (비율 유지)
    width, height = img.size
    min_dimension = min(width, height)
    
    left = (width - min_dimension) // 2
    top = (height - min_dimension) // 2
    right = left + min_dimension
    bottom = top + min_dimension
    
    cropped = img.crop((left, top, right, bottom))
    
    # 원하는 크기로 리사이징
    resized = cropped.resize(size, Image.Resampling.LANCZOS)
    
    # RGB로 변환 (JPEG 저장용)
    if resized.mode == 'RGBA':
        # 투명 배경을 흰색으로 변환
        rgb_image = Image.new('RGB', resized.size, (255, 255, 255))
        rgb_image.paste(resized, mask=resized.split()[3])
        return rgb_image
    elif resized.mode != 'RGB':
        return resized.convert('RGB')
    
    return resized


def generate_resized_key(original_key: str, shape: str, size: tuple) -> str:
    """
    리사이징된 이미지의 S3 키 생성
    
    Args:
        original_key: 원본 S3 키
        shape: 'circular' 또는 'square'
        size: (width, height) 튜플
    
    Returns:
        리사이징된 이미지 S3 키
    
    예:
        media/images/artists/original/xxx.jpg
        -> media/images/artists/circular/228x228/xxx.png (원형)
        -> media/images/artists/square/220x220/xxx.jpg (사각형)
    """
    # 파일명 추출
    filename = original_key.split('/')[-1]
    
    # 확장자 변경 (원형은 PNG, 사각형은 JPEG)
    if shape == 'circular':
        filename_without_ext = filename.rsplit('.', 1)[0]
        filename = f"{filename_without_ext}.png"
    else:
        # JPEG로 변환
        filename_without_ext = filename.rsplit('.', 1)[0]
        filename = f"{filename_without_ext}.jpg"
    
    # 크기 문자열
    size_str = f"{size[0]}x{size[1]}"
    
    # 경로 생성 (original을 shape/size로 교체)
    new_key = original_key.replace('/original/', f'/{shape}/{size_str}/')
    
    # 파일명 교체
    new_key = '/'.join(new_key.split('/')[:-1]) + '/' + filename
    
    return new_key


def upload_resized_image_to_s3(s3_key: str, image: Image.Image, format: str = 'JPEG'):
    """
    리사이징된 이미지를 S3에 업로드합니다.
    
    Args:
        s3_key: S3 키
        image: PIL Image 객체
        format: 이미지 포맷 ('JPEG' 또는 'PNG')
    """
    s3_client = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    
    img_buffer = io.BytesIO()
    
    if format == 'PNG':
        image.save(img_buffer, format='PNG', optimize=True)
        content_type = 'image/png'
    else:
        image.save(img_buffer, format='JPEG', quality=85, optimize=True)
        content_type = 'image/jpeg'
    
    img_buffer.seek(0)
    
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=img_buffer,
        ContentType=content_type,
        CacheControl='max-age=31536000'  # 1년 캐시
    )


def resize_image_from_s3(s3_key: str, image_type: str) -> dict:
    """
    S3의 이미지를 리사이징합니다.
    
    Args:
        s3_key: S3 키 (예: media/images/artists/original/xxx.jpg)
        image_type: 이미지 타입 ('artists', 'albums', 'tracks')
        
    Returns:
        리사이징된 이미지 URL 딕셔너리
    """
    # 이미지 파일 확인
    if not is_image_file(s3_key):
        logger.warning(f"[이미지 리사이징] 이미지 파일이 아님, 스킵: {s3_key}")
        return {}
    
    # 원본 이미지가 아니면 스킵 (무한 루프 방지)
    if '/original/' not in s3_key:
        logger.warning(f"[이미지 리사이징] 원본이 아닌 이미지, 스킵: {s3_key}")
        return {}
    
    # 이미지 타입 확인
    if not image_type or image_type not in RESIZE_CONFIG:
        logger.warning(f"[이미지 리사이징] 알 수 없는 이미지 타입, 스킵: {image_type}")
        return {}
    
    # 리사이징 설정 가져오기
    config = RESIZE_CONFIG.get(image_type)
    if not config:
        logger.warning(f"[이미지 리사이징] 리사이징 설정 없음, 스킵: {image_type}")
        return {}
    
    try:
        logger.info(f"[이미지 리사이징] 시작: s3_key={s3_key}, type={image_type}")
        
        # 원본 이미지 다운로드
        image = download_image_from_s3(s3_key)
        
        resized_urls = {}
        
        # 원형 이미지 생성
        for size in config.get('circular', []):
            circular_image = create_circular_image(image, size[0])
            circular_key = generate_resized_key(s3_key, 'circular', size)
            upload_resized_image_to_s3(circular_key, circular_image, format='PNG')
            resized_urls[f'circular_{size[0]}x{size[1]}'] = get_s3_url(circular_key)
            logger.info(f"[이미지 리사이징] 원형 이미지 생성 완료: {circular_key}")
        
        # 사각형 이미지 생성
        for size in config.get('square', []):
            square_image = create_square_image(image, size)
            square_key = generate_resized_key(s3_key, 'square', size)
            upload_resized_image_to_s3(square_key, square_image, format='JPEG')
            resized_urls[f'square_{size[0]}x{size[1]}'] = get_s3_url(square_key)
            logger.info(f"[이미지 리사이징] 사각형 이미지 생성 완료: {square_key}")
        
        logger.info(f"[이미지 리사이징] 완료: {s3_key}")
        return resized_urls
        
    except Exception as e:
        logger.error(f"[이미지 리사이징] 실패: {s3_key}, 오류: {e}", exc_info=True)
        raise
