"""
이미지 리사이징 Lambda 함수

S3에 이미지가 업로드되면 자동으로 리사이징합니다.
- 아티스트 이미지: 원형 2개 (228x228, 208x208) + 사각형 1개 (220x220)
- 앨범 이미지: 사각형 1개 (220x220)
- 트랙 이미지: 사각형 1개 (48x48)
"""

import json
import boto3
from PIL import Image, ImageDraw
import io
import os
import logging
from urllib.parse import unquote_plus

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 클라이언트
s3_client = boto3.client('s3')

# 이미지 타입별 리사이징 설정
RESIZE_CONFIG = {
    'artists': {
        'circular': [(228, 228), (208, 208)],  # 원형 이미지
        'square': [(220, 220)]  # 사각형 이미지
    },
    'albums': {
        'circular': [],  # 원형 필요 없음
        'square': [(220, 220)]
    },
    'tracks': {
        'circular': [],  # 원형 필요 없음
        'square': [(48, 48)]
    }
}


def lambda_handler(event, context):
    """
    S3 이벤트를 받아 이미지를 리사이징합니다.
    
    Args:
        event: S3 이벤트 (PUT 트리거)
        context: Lambda 컨텍스트
        
    Returns:
        처리 결과
    """
    logger.info(f"이벤트 수신: {json.dumps(event)}")
    
    processed_count = 0
    error_count = 0
    
    for record in event.get('Records', []):
        try:
            # S3 정보 추출
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"처리 시작: bucket={bucket}, key={key}")
            
            # 이미지 파일 확인
            if not is_image_file(key):
                logger.info(f"이미지 파일이 아님, 스킵: {key}")
                continue
            
            # 이미 리사이징된 이미지면 스킵 (무한 루프 방지)
            if '/original/' not in key:
                logger.info(f"원본이 아닌 이미지, 스킵: {key}")
                continue
            
            # 이미지 타입 추출 (artists, albums, tracks)
            image_type = extract_image_type(key)
            if not image_type:
                logger.warning(f"알 수 없는 이미지 타입, 스킵: {key}")
                continue
            
            # 리사이징 설정 가져오기
            config = RESIZE_CONFIG.get(image_type)
            if not config:
                logger.warning(f"리사이징 설정 없음, 스킵: {image_type}")
                continue
            
            # 원본 이미지 다운로드
            image = download_image_from_s3(bucket, key)
            
            # 원형 이미지 생성
            for size in config.get('circular', []):
                circular_image = create_circular_image(image, size[0])
                circular_key = generate_resized_key(key, 'circular', size)
                upload_image_to_s3(bucket, circular_key, circular_image, format='PNG')
                logger.info(f"원형 이미지 생성 완료: {circular_key}")
            
            # 사각형 이미지 생성
            for size in config.get('square', []):
                square_image = create_square_image(image, size)
                square_key = generate_resized_key(key, 'square', size)
                upload_image_to_s3(bucket, square_key, square_image, format='JPEG')
                logger.info(f"사각형 이미지 생성 완료: {square_key}")
            
            processed_count += 1
            logger.info(f"처리 완료: {key}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"처리 실패: {str(e)}", exc_info=True)
    
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'message': '이미지 리사이징 완료',
            'processed': processed_count,
            'errors': error_count
        }, ensure_ascii=False)
    }
    
    logger.info(f"처리 결과: {result}")
    return result


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


def download_image_from_s3(bucket: str, key: str) -> Image.Image:
    """S3에서 이미지 다운로드"""
    response = s3_client.get_object(Bucket=bucket, Key=key)
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


def upload_image_to_s3(bucket: str, key: str, image: Image.Image, format: str = 'JPEG'):
    """
    이미지를 S3에 업로드합니다.
    
    Args:
        bucket: S3 버킷 이름
        key: S3 키
        image: PIL Image 객체
        format: 이미지 포맷 ('JPEG' 또는 'PNG')
    """
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
        Key=key,
        Body=img_buffer,
        ContentType=content_type,
        CacheControl='max-age=31536000'  # 1년 캐시
    )
