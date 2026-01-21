"""
이미지 리사이징 Celery 태스크

S3에 업로드된 이미지를 자동으로 리사이징합니다.
"""
from celery import shared_task
from music.utils.image_resizer import resize_image_from_s3, extract_image_type, get_s3_url
from music.models import Albums, Artists
from django.utils import timezone
import logging
import re

logger = logging.getLogger(__name__)


def extract_entity_id_from_s3_key(s3_key: str) -> int:
    """
    S3 키에서 엔티티 ID 추출
    
    예: media/images/albums/original/123_album_name_20260121_112022.jpg -> 123
    """
    match = re.search(r'/(\d+)_', s3_key)
    if match:
        return int(match.group(1))
    return None


@shared_task(bind=True, max_retries=3)
def resize_image_task(self, s3_key: str, image_type: str = None, entity_id: int = None):
    """
    S3에 업로드된 이미지를 리사이징합니다.
    
    Args:
        s3_key: S3 키 (예: media/images/artists/original/xxx.jpg)
        image_type: 이미지 타입 ('artists', 'albums', 'tracks'). None이면 자동 추출
        entity_id: 엔티티 ID (앨범/아티스트 ID). None이면 S3 키에서 추출
        
    Returns:
        리사이징된 이미지 URL 딕셔너리
    """
    try:
        # image_type이 없으면 자동 추출
        if not image_type:
            image_type = extract_image_type(s3_key)
            if not image_type:
                logger.warning(f"[이미지 리사이징] 이미지 타입을 추출할 수 없음: {s3_key}")
                return {}
        
        # entity_id가 없으면 S3 키에서 추출
        if not entity_id:
            entity_id = extract_entity_id_from_s3_key(s3_key)
        
        logger.info(f"[이미지 리사이징] 태스크 시작: s3_key={s3_key}, type={image_type}, entity_id={entity_id}")
        
        resized_urls = resize_image_from_s3(s3_key, image_type)
        
        logger.info(f"[이미지 리사이징] 태스크 완료: {s3_key}")
        logger.info(f"  생성된 이미지: {list(resized_urls.keys())}")
        
        # 리사이징 완료 후 DB 업데이트 (앨범의 경우 image_large_square 저장)
        if image_type == 'albums' and entity_id:
            try:
                album = Albums.objects.get(album_id=entity_id, is_deleted=False)
                
                # 리사이징된 URL 매핑
                square_220_url = resized_urls.get('square_220x220')
                square_360_url = resized_urls.get('square_360x360')
                
                logger.info(f"[이미지 리사이징] DB 업데이트 체크: album_id={entity_id}, square_220={bool(square_220_url)}, square_360={bool(square_360_url)}")
                logger.info(f"  현재 상태: image_square={bool(album.image_square)}, image_large_square={bool(album.image_large_square)}")
                
                update_fields = []
                # 실제 리사이징이 완료되었으므로 항상 업데이트 (예상 URL을 실제 URL로 교체)
                if square_220_url:
                    if album.image_square != square_220_url:
                        album.image_square = square_220_url
                        update_fields.append('image_square')
                        logger.info(f"  image_square 업데이트: {square_220_url[:60]}...")
                
                if square_360_url:
                    if album.image_large_square != square_360_url:
                        album.image_large_square = square_360_url
                        update_fields.append('image_large_square')
                        logger.info(f"  image_large_square 업데이트: {square_360_url[:60]}...")
                
                if update_fields:
                    album.updated_at = timezone.now()
                    update_fields.append('updated_at')
                    album.save(update_fields=update_fields)
                    logger.info(f"[이미지 리사이징] ✅ 앨범 DB 업데이트 완료: album_id={entity_id}, fields={update_fields}")
                else:
                    logger.info(f"[이미지 리사이징] 앨범 DB 업데이트 불필요 (이미 모든 필드가 있음): album_id={entity_id}")
            
            except Albums.DoesNotExist:
                logger.warning(f"[이미지 리사이징] 앨범을 찾을 수 없음: album_id={entity_id}")
            except Exception as e:
                logger.error(f"[이미지 리사이징] 앨범 DB 업데이트 실패: album_id={entity_id}, 오류: {e}", exc_info=True)
        
        elif image_type == 'artists' and entity_id:
            try:
                artist = Artists.objects.get(artist_id=entity_id, is_deleted=False)
                
                # 리사이징된 URL 매핑
                large_circle_url = resized_urls.get('circular_228x228')
                small_circle_url = resized_urls.get('circular_208x208')
                square_url = resized_urls.get('square_220x220')
                
                update_fields = []
                # 실제 리사이징이 완료되었으므로 항상 업데이트 (예상 URL을 실제 URL로 교체)
                if large_circle_url:
                    if artist.image_large_circle != large_circle_url:
                        artist.image_large_circle = large_circle_url
                        update_fields.append('image_large_circle')
                        logger.info(f"  image_large_circle 업데이트: {large_circle_url[:60]}...")
                
                if small_circle_url:
                    if artist.image_small_circle != small_circle_url:
                        artist.image_small_circle = small_circle_url
                        update_fields.append('image_small_circle')
                        logger.info(f"  image_small_circle 업데이트: {small_circle_url[:60]}...")
                
                if square_url:
                    if artist.image_square != square_url:
                        artist.image_square = square_url
                        update_fields.append('image_square')
                        logger.info(f"  image_square 업데이트: {square_url[:60]}...")
                
                if update_fields:
                    artist.updated_at = timezone.now()
                    update_fields.append('updated_at')
                    artist.save(update_fields=update_fields)
                    logger.info(f"[이미지 리사이징] 아티스트 DB 업데이트 완료: artist_id={entity_id}, fields={update_fields}")
            
            except Artists.DoesNotExist:
                logger.warning(f"[이미지 리사이징] 아티스트를 찾을 수 없음: artist_id={entity_id}")
            except Exception as e:
                logger.error(f"[이미지 리사이징] 아티스트 DB 업데이트 실패: artist_id={entity_id}, 오류: {e}")
        
        return resized_urls
        
    except Exception as e:
        logger.error(f"[이미지 리사이징] 태스크 실패: {s3_key}, 오류: {e}", exc_info=True)
        
        if self.request.retries < self.max_retries:
            logger.info(f"[이미지 리사이징] 재시도: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=60)
        
        raise
