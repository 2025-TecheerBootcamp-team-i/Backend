"""
기존 이미지 URL을 S3로 마이그레이션하는 Management Command

사용법:
    python manage.py migrate_images_to_s3 --type=artist
    python manage.py migrate_images_to_s3 --type=album
    python manage.py migrate_images_to_s3 --type=all
    python manage.py migrate_images_to_s3 --type=artist --limit=10 --dry-run
"""

import re
import time
import random
import requests
import boto3
from io import BytesIO
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from music.models import Artists, Albums
from music.services.deezer import DeezerService
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '기존 아티스트/앨범 이미지를 S3로 마이그레이션합니다.'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 재사용 가능한 HTTP 세션 생성 (429 에러 방지)
        self.http_session = requests.Session()
        headers = {
            "User-Agent": "MusicBackendService/1.0 (contact: admin@musicbackend.com)",
            "Accept": "application/json, image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.wikipedia.org/"
        }
        self.http_session.headers.update(headers)
        
        # Retry 전략 설정
        retries = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"])
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.http_session.mount("https://", adapter)
        self.http_session.mount("http://", adapter)

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['artist', 'album', 'all'],
            default='all',
            help='마이그레이션할 이미지 타입 (artist, album, all)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='처리할 최대 개수 (테스트용)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 업로드 없이 테스트만 수행'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='이미 S3 URL인 경우 스킵 (기본: True)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=5,
            help='배치 처리 크기 (기본 5개, API 레이트 리밋 방지)'
        )

    def handle(self, *args, **options):
        image_type = options['type']
        limit = options['limit']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']
        batch_size = options['batch_size']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('이미지 S3 마이그레이션 시작'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY-RUN 모드: 실제 업로드 없이 테스트만 수행합니다.'))
        
        # S3 클라이언트 생성
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        total_stats = {'processed': 0, 'success': 0, 'skipped': 0, 'failed': 0}
        start_time = time.time()
        
        # 아티스트 이미지 처리
        if image_type in ['artist', 'all']:
            self.stdout.write(self.style.SUCCESS('\n👤 아티스트 이미지 처리 시작...'))
            stats = self.migrate_artist_images(limit, dry_run, skip_existing, batch_size)
            for key in total_stats:
                total_stats[key] += stats[key]
        
        # 앨범 이미지 처리
        if image_type in ['album', 'all']:
            self.stdout.write(self.style.SUCCESS('\n💿 앨범 이미지 처리 시작...'))
            stats = self.migrate_album_images(limit, dry_run, skip_existing, batch_size)
            for key in total_stats:
                total_stats[key] += stats[key]
        
        elapsed_time = time.time() - start_time
        
        # 결과 출력
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('마이그레이션 완료'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'총 처리: {total_stats["processed"]}개')
        self.stdout.write(self.style.SUCCESS(f'✅ 성공: {total_stats["success"]}개'))
        self.stdout.write(self.style.WARNING(f'⏭️  스킵: {total_stats["skipped"]}개'))
        self.stdout.write(self.style.ERROR(f'❌ 실패: {total_stats["failed"]}개'))
        self.stdout.write(f'소요 시간: {elapsed_time:.2f}초')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN 모드였으므로 실제 업로드는 수행되지 않았습니다.'))

    def migrate_artist_images(self, limit, dry_run, skip_existing, batch_size):
        """아티스트 이미지 마이그레이션"""
        from django.db import connection
        
        # artist_id 1부터 시작, artist_image가 null이 아니고, 
        # image_square, image_small_circle, image_large_circle이 모두 null인 것만 조회
        with connection.cursor() as cursor:
            query = """
                SELECT artist_id FROM artists
                WHERE artist_image IS NOT NULL 
                AND artist_image != ''
                AND is_deleted = FALSE
                AND (image_square IS NULL OR image_small_circle IS NULL OR image_large_circle IS NULL)
                ORDER BY artist_id ASC
            """
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query)
            artist_ids = [row[0] for row in cursor.fetchall()]
        
        total = len(artist_ids)
        self.stdout.write(f'처리 대상: {total}개 아티스트 (artist_id 1부터 시작)')
        
        stats = {'processed': 0, 'success': 0, 'skipped': 0, 'failed': 0}
        start_time = time.time()
        
        for i, artist_id in enumerate(artist_ids, 1):
            try:
                artist = Artists.objects.get(artist_id=artist_id)
                
                # artist_image가 null이면 스킵
                if not artist.artist_image or artist.artist_image.strip() == '':
                    self.stdout.write(
                        self.style.WARNING(f'[{i}/{total}] ⏭️  스킵 (artist_image null): {artist.artist_name}')
                    )
                    stats['skipped'] += 1
                    stats['processed'] += 1
                    continue
                
                # 이미 square, circle이 모두 있으면 스킵
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT image_square, image_small_circle, image_large_circle 
                        FROM artists WHERE artist_id = %s
                    """, [artist_id])
                    row = cursor.fetchone()
                    if row and all(row):  # 모두 null이 아니면
                        self.stdout.write(
                            self.style.WARNING(f'[{i}/{total}] ⏭️  스킵 (이미 처리됨): {artist.artist_name}')
                        )
                        stats['skipped'] += 1
                        stats['processed'] += 1
                        continue
                
                # 유효성 체크
                if not self.is_valid_url(artist.artist_image):
                    self.stdout.write(
                        self.style.WARNING(f'[{i}/{total}] ⏭️  스킵 (유효하지 않은 URL): {artist.artist_name}')
                    )
                    stats['skipped'] += 1
                    stats['processed'] += 1
                    continue
                
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f'[{i}/{total}] (DRY-RUN) 업로드 예정: {artist.artist_name} (ID: {artist_id})')
                    )
                    stats['success'] += 1
                else:
                    # S3 업로드 (429 에러 시 Deezer API로 fallback)
                    use_deezer = False
                    try:
                        s3_url = self.upload_image_to_s3(
                            image_url=artist.artist_image,
                            image_type='artists',
                            entity_id=artist.artist_id,
                            entity_name=artist.artist_name
                        )
                    except requests.exceptions.HTTPError as e:
                        # 429 에러면 Deezer API로 시도
                        if '429' in str(e) and 'wikimedia' in artist.artist_image.lower():
                            self.stdout.write(
                                self.style.WARNING(f'[{i}/{total}] ⚠️  Wikimedia 429 에러, Deezer API로 재시도: {artist.artist_name}')
                            )
                            # Deezer API로 이미지 조회
                            deezer_url = DeezerService.fetch_artist_image(artist.artist_name)
                            if deezer_url:
                                try:
                                    s3_url = self.upload_image_to_s3(
                                        image_url=deezer_url,
                                        image_type='artists',
                                        entity_id=artist.artist_id,
                                        entity_name=artist.artist_name
                                    )
                                    self.stdout.write(
                                        self.style.SUCCESS(f'[{i}/{total}] ✅ 완료 (Deezer): {artist.artist_name} (ID: {artist_id})')
                                    )
                                    use_deezer = True  # Deezer 성공 플래그
                                except Exception as deezer_error:
                                    self.stdout.write(
                                        self.style.ERROR(f'[{i}/{total}] ❌ Deezer도 실패: {artist.artist_name} - {str(deezer_error)}')
                                    )
                                    raise
                            else:
                                raise  # Deezer에서도 못 찾으면 원래 에러 그대로
                        else:
                            raise  # 429가 아니면 그대로
                    
                    # DB 업데이트 (artist_image 업데이트)
                    artist.artist_image = s3_url
                    artist.save(update_fields=['artist_image'])
                    
                    # 리사이징된 이미지 URL 계산 및 DB 업데이트 (직접 SQL 사용)
                    # S3에 업로드되면 Lambda가 자동으로 리사이징하므로 URL만 계산해서 저장
                    if '/original/' in s3_url:
                        from django.db import connection
                        filename = s3_url.split('/original/')[-1]
                        filename_without_ext = filename.rsplit('.', 1)[0]
                        
                        base_url = f'https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com'
                        image_square = f'{base_url}/media/images/artists/square/220x220/{filename_without_ext}.jpg'
                        image_small_circle = f'{base_url}/media/images/artists/circular/208x208/{filename_without_ext}.png'
                        image_large_circle = f'{base_url}/media/images/artists/circular/228x228/{filename_without_ext}.png'
                        
                        # DB 업데이트 (리사이징된 URL 저장 - 직접 SQL)
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                UPDATE artists 
                                SET image_square = %s,
                                    image_small_circle = %s,
                                    image_large_circle = %s
                                WHERE artist_id = %s
                            """, [image_square, image_small_circle, image_large_circle, artist_id])
                    
                    # Deezer 성공이 아니면 일반 성공 메시지 출력
                    if not use_deezer:
                        self.stdout.write(
                            self.style.SUCCESS(f'[{i}/{total}] ✅ 완료: {artist.artist_name} (ID: {artist_id})')
                        )
                    stats['success'] += 1
                
                stats['processed'] += 1
                
                # 진행 현황 표시 (10개마다 또는 마지막)
                if i % 10 == 0 or i == total:
                    elapsed = time.time() - start_time
                    percent = (i / total * 100) if total > 0 else 0
                    speed = i / elapsed if elapsed > 0 else 0
                    remaining = total - i
                    eta_seconds = remaining / speed if speed > 0 else 0
                    eta_minutes = eta_seconds / 60
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'\n📊 진행 현황: {i}/{total} ({percent:.1f}%) | '
                            f'성공: {stats["success"]} | 스킵: {stats["skipped"]} | 실패: {stats["failed"]} | '
                            f'속도: {speed:.1f}개/초 | 예상 남은 시간: {eta_minutes:.1f}분'
                        )
                    )
                
                # 배치 처리 후 잠시 대기 (차단 방지: 랜덤 슬립)
                if not dry_run:
                    # Wikimedia URL인 경우 더 긴 대기
                    if 'wikimedia' in artist.artist_image.lower() if artist.artist_image else False:
                        sleep_time = random.uniform(0.8, 1.5)  # 0.8~1.5초 랜덤
                    else:
                        sleep_time = random.uniform(0.3, 0.7)  # 0.3~0.7초 랜덤
                    time.sleep(sleep_time)
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[{i}/{total}] ❌ 실패: artist_id={artist_id} - {str(e)}')
                )
                logger.error(f'아티스트 이미지 마이그레이션 실패: {artist_id}, 오류: {e}')
                stats['failed'] += 1
                stats['processed'] += 1
        
        return stats

    def migrate_album_images(self, limit, dry_run, skip_existing, batch_size):
        """앨범 이미지 마이그레이션"""
        # 이미지가 있고 삭제되지 않은 앨범 조회
        albums = Albums.objects.filter(
            album_image__isnull=False,
            is_deleted=False
        ).exclude(album_image='').select_related('artist')
        
        if limit:
            albums = albums[:limit]
        
        total = albums.count()
        self.stdout.write(f'처리 대상: {total}개 앨범')
        
        stats = {'processed': 0, 'success': 0, 'skipped': 0, 'failed': 0}
        
        for i, album in enumerate(albums, 1):
            try:
                # S3 URL 체크
                if skip_existing and self.is_s3_url(album.album_image):
                    self.stdout.write(
                        self.style.WARNING(f'[{i}/{total}] ⏭️  스킵 (이미 S3): {album.album_name}')
                    )
                    stats['skipped'] += 1
                    stats['processed'] += 1
                    continue
                
                # 유효성 체크
                if not self.is_valid_url(album.album_image):
                    self.stdout.write(
                        self.style.WARNING(f'[{i}/{total}] ⏭️  스킵 (유효하지 않은 URL): {album.album_name}')
                    )
                    stats['skipped'] += 1
                    stats['processed'] += 1
                    continue
                
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f'[{i}/{total}] (DRY-RUN) 업로드 예정: {album.album_name}')
                    )
                    stats['success'] += 1
                else:
                    # S3 업로드
                    s3_url = self.upload_image_to_s3(
                        image_url=album.album_image,
                        image_type='albums',
                        entity_id=album.album_id,
                        entity_name=album.album_name
                    )
                    
                    # DB 업데이트
                    album.album_image = s3_url
                    album.save(update_fields=['album_image'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'[{i}/{total}] ✅ 완료: {album.album_name}')
                    )
                    stats['success'] += 1
                
                stats['processed'] += 1
                
                # 배치 처리 후 잠시 대기 (Wikimedia rate limit 방지)
                if i % batch_size == 0 and not dry_run:
                    time.sleep(3)  # 1초 → 3초로 증가
                elif not dry_run:
                    time.sleep(0.5)  # 각 요청 사이에도 짧은 대기
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[{i}/{total}] ❌ 실패: {album.album_name} - {str(e)}')
                )
                logger.error(f'앨범 이미지 마이그레이션 실패: {album.album_id}, 오류: {e}')
                stats['failed'] += 1
                stats['processed'] += 1
        
        return stats

    def upload_image_to_s3(self, image_url: str, image_type: str, entity_id: int, entity_name: str) -> str:
        """
        이미지를 다운로드하여 S3에 업로드합니다.
        
        Args:
            image_url: 다운로드할 이미지 URL
            image_type: 'artists' 또는 'albums'
            entity_id: 아티스트/앨범 ID
            entity_name: 아티스트/앨범 이름 (파일명에 포함)
            
        Returns:
            S3 URL (original 폴더)
        """
        # 이미 S3 URL이면 그대로 반환 (다시 업로드 불필요)
        if self.is_s3_url(image_url):
            return image_url
        
        # 이미지 다운로드 (429 에러는 Retry-After 헤더 존중)
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Wikimedia URL인 경우 요청 전 랜덤 대기 (429 방지)
                is_wikimedia = 'wikimedia' in image_url.lower() if image_url else False
                if is_wikimedia and attempt == 0:  # 첫 시도만 대기
                    wait_time = random.uniform(0.5, 1.2)
                    time.sleep(wait_time)
                
                response = self.http_session.get(image_url, timeout=30, stream=True)
                
                # 429 Too Many Requests 에러 처리 (Retry-After 헤더 존중)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = int(retry_after) if (retry_after and retry_after.isdigit()) else 30
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  429 Too Many Requests. {wait}초 대기 후 재시도... ({attempt + 1}/{max_attempts})')
                    )
                    time.sleep(wait)
                    attempt += 1
                    continue
                
                # 5xx 서버 에러 처리
                if response.status_code >= 500:
                    wait = 3 + attempt * 2
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  서버 에러({response.status_code}). {wait}초 대기 후 재시도... ({attempt + 1}/{max_attempts})')
                    )
                    time.sleep(wait)
                    attempt += 1
                    continue
                
                response.raise_for_status()
                image_content = response.content
                break  # 성공하면 루프 종료
                
            except requests.exceptions.HTTPError as e:
                # HTTPError는 위에서 처리됨 (429, 5xx 등)
                attempt += 1
                if attempt >= max_attempts:
                    raise
            except requests.exceptions.RequestException as e:
                attempt += 1
                wait = 3 + attempt * 2
                self.stdout.write(
                    self.style.WARNING(f'⚠️  요청 오류: {str(e)[:50]}... / {wait}초 대기 후 재시도 ({attempt}/{max_attempts})')
                )
                if attempt < max_attempts:
                    time.sleep(wait)
                    continue
                else:
                    raise
        
        # 파일명 생성 (아티스트/앨범 이름 포함)
        safe_name = self.sanitize_filename(entity_name)
        timestamp = timezone.now().strftime('%Y%m%d')
        file_extension = self.get_image_extension(image_url, image_content)
        file_name = f'{entity_id}_{safe_name}_{timestamp}.{file_extension}'
        
        # S3 키 생성
        s3_key = f'media/images/{image_type}/original/{file_name}'
        
        # Content-Type 결정
        content_type = self.get_content_type(file_extension)
        
        # S3에 업로드
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=image_content,
            ContentType=content_type
        )
        
        # S3 URL 생성
        s3_url = f'https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}'
        
        return s3_url

    def sanitize_filename(self, name: str) -> str:
        """
        파일명에 사용할 수 있도록 이름을 정리합니다.
        
        - 특수문자 제거
        - 공백을 언더스코어로 변환
        - 길이 제한 (50자)
        """
        if not name:
            return 'unknown'
        
        # 특수문자 제거 (한글, 영문, 숫자, 공백만 허용)
        safe_name = re.sub(r'[^\w\s가-힣]', '', name)
        
        # 공백을 언더스코어로 변환
        safe_name = safe_name.replace(' ', '_')
        
        # 연속된 언더스코어 제거
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # 앞뒤 언더스코어 제거
        safe_name = safe_name.strip('_')
        
        # 길이 제한
        if len(safe_name) > 50:
            safe_name = safe_name[:50]
        
        # 빈 문자열이면 기본값
        if not safe_name:
            return 'unknown'
        
        return safe_name

    def get_image_extension(self, url: str, content: bytes = None) -> str:
        """이미지 확장자 추출"""
        # URL에서 확장자 추출
        url_ext = url.split('.')[-1].split('?')[0].lower()
        if url_ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
            return 'jpg' if url_ext == 'jpeg' else url_ext
        
        # Content에서 추출 시도
        if content:
            # JPEG 시그니처
            if content[:2] == b'\xff\xd8':
                return 'jpg'
            # PNG 시그니처
            if content[:8] == b'\x89PNG\r\n\x1a\n':
                return 'png'
            # WebP 시그니처
            if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
                return 'webp'
            # GIF 시그니처
            if content[:6] in [b'GIF87a', b'GIF89a']:
                return 'gif'
        
        # 기본값
        return 'jpg'

    def get_content_type(self, extension: str) -> str:
        """확장자에 따른 Content-Type 반환"""
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
            'gif': 'image/gif'
        }
        return content_types.get(extension.lower(), 'image/jpeg')

    def is_s3_url(self, url: str) -> bool:
        """S3 URL인지 확인"""
        if not url:
            return False
        return 's3.amazonaws.com' in url or '.s3.' in url or self.bucket_name in url

    def is_valid_url(self, url: str) -> bool:
        """유효한 URL인지 확인"""
        if not url or not url.strip():
            return False
        return url.startswith('http://') or url.startswith('https://')
