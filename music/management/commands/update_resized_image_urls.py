"""
리사이징된 이미지 URL을 DB에 업데이트하는 Management Command

사용법:
    python manage.py update_resized_image_urls --type=artist
    python manage.py update_resized_image_urls --type=album
    python manage.py update_resized_image_urls --type=all
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from music.models import Artists, Albums
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'S3에 업로드된 원본 이미지 URL을 기반으로 리사이징된 이미지 URL을 DB에 업데이트합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['artist', 'album', 'all'],
            default='all',
            help='업데이트할 이미지 타입 (artist, album, all)'
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
            help='실제 업데이트 없이 테스트만 수행'
        )

    def handle(self, *args, **options):
        image_type = options['type']
        limit = options['limit']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('리사이징된 이미지 URL 업데이트 시작'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY-RUN 모드: 실제 업데이트 없이 테스트만 수행합니다.'))
        
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        region = settings.AWS_S3_REGION_NAME
        base_url = f'https://{bucket_name}.s3.{region}.amazonaws.com'
        
        total_stats = {'processed': 0, 'success': 0, 'skipped': 0, 'failed': 0}
        
        # 아티스트 이미지 업데이트
        if image_type in ['artist', 'all']:
            self.stdout.write(self.style.SUCCESS('\n👤 아티스트 이미지 URL 업데이트 시작...'))
            stats = self.update_artist_images(base_url, limit, dry_run)
            for key in total_stats:
                total_stats[key] += stats[key]
        
        # 앨범 이미지 업데이트
        if image_type in ['album', 'all']:
            self.stdout.write(self.style.SUCCESS('\n💿 앨범 이미지 URL 업데이트 시작...'))
            stats = self.update_album_images(base_url, limit, dry_run)
            for key in total_stats:
                total_stats[key] += stats[key]
        
        # 결과 출력
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('업데이트 완료'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'총 처리: {total_stats["processed"]}개')
        self.stdout.write(self.style.SUCCESS(f'✅ 성공: {total_stats["success"]}개'))
        self.stdout.write(self.style.WARNING(f'⏭️  스킵: {total_stats["skipped"]}개'))
        self.stdout.write(self.style.ERROR(f'❌ 실패: {total_stats["failed"]}개'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN 모드였으므로 실제 업데이트는 수행되지 않았습니다.'))

    def update_artist_images(self, base_url: str, limit, dry_run):
        """아티스트 이미지 URL 업데이트"""
        # S3 URL이 있는 아티스트만 조회
        artists = Artists.objects.filter(
            artist_image__isnull=False,
            is_deleted=False
        ).exclude(artist_image='')
        
        # S3 URL만 필터링
        artists = [a for a in artists if 's3.amazonaws.com' in a.artist_image or '.s3.' in a.artist_image]
        
        if limit:
            artists = artists[:limit]
        
        total = len(artists)
        self.stdout.write(f'처리 대상: {total}개 아티스트')
        
        stats = {'processed': 0, 'success': 0, 'skipped': 0, 'failed': 0}
        
        for i, artist in enumerate(artists, 1):
            try:
                # 원본 이미지 URL에서 파일명 추출
                original_url = artist.artist_image
                if '/original/' not in original_url:
                    self.stdout.write(
                        self.style.WARNING(f'[{i}/{total}] ⏭️  스킵 (원본 경로 없음): {artist.artist_name}')
                    )
                    stats['skipped'] += 1
                    stats['processed'] += 1
                    continue
                
                # 파일명 추출
                filename = original_url.split('/original/')[-1]
                filename_without_ext = filename.rsplit('.', 1)[0]
                
                # 리사이징된 이미지 URL 생성
                image_square = f'{base_url}/media/images/artists/square/220x220/{filename_without_ext}.jpg'
                image_small_circle = f'{base_url}/media/images/artists/circular/208x208/{filename_without_ext}.png'
                image_large_circle = f'{base_url}/media/images/artists/circular/228x228/{filename_without_ext}.png'
                
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f'[{i}/{total}] (DRY-RUN) 업데이트 예정: {artist.artist_name}')
                    )
                    stats['success'] += 1
                else:
                    # DB 업데이트
                    artist.image_square = image_square
                    artist.image_small_circle = image_small_circle
                    artist.image_large_circle = image_large_circle
                    artist.save(update_fields=['image_square', 'image_small_circle', 'image_large_circle'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'[{i}/{total}] ✅ 완료: {artist.artist_name}')
                    )
                    stats['success'] += 1
                
                stats['processed'] += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[{i}/{total}] ❌ 실패: {artist.artist_name} - {str(e)}')
                )
                logger.error(f'아티스트 이미지 URL 업데이트 실패: {artist.artist_id}, 오류: {e}')
                stats['failed'] += 1
                stats['processed'] += 1
        
        return stats

    def update_album_images(self, base_url: str, limit, dry_run):
        """앨범 이미지 URL 업데이트"""
        # S3 URL이 있는 앨범만 조회
        albums = Albums.objects.filter(
            album_image__isnull=False,
            is_deleted=False
        ).exclude(album_image='')
        
        # S3 URL만 필터링
        albums = [a for a in albums if 's3.amazonaws.com' in a.album_image or '.s3.' in a.album_image]
        
        if limit:
            albums = albums[:limit]
        
        total = len(albums)
        self.stdout.write(f'처리 대상: {total}개 앨범')
        
        stats = {'processed': 0, 'success': 0, 'skipped': 0, 'failed': 0}
        
        for i, album in enumerate(albums, 1):
            try:
                # 원본 이미지 URL에서 파일명 추출
                original_url = album.album_image
                if '/original/' not in original_url:
                    self.stdout.write(
                        self.style.WARNING(f'[{i}/{total}] ⏭️  스킵 (원본 경로 없음): {album.album_name}')
                    )
                    stats['skipped'] += 1
                    stats['processed'] += 1
                    continue
                
                # 파일명 추출
                filename = original_url.split('/original/')[-1]
                filename_without_ext = filename.rsplit('.', 1)[0]
                
                # 리사이징된 이미지 URL 생성
                image_square = f'{base_url}/media/images/albums/square/220x220/{filename_without_ext}.jpg'
                
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f'[{i}/{total}] (DRY-RUN) 업데이트 예정: {album.album_name}')
                    )
                    stats['success'] += 1
                else:
                    # DB 업데이트
                    album.image_square = image_square
                    album.save(update_fields=['image_square'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'[{i}/{total}] ✅ 완료: {album.album_name}')
                    )
                    stats['success'] += 1
                
                stats['processed'] += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'[{i}/{total}] ❌ 실패: {album.album_name} - {str(e)}')
                )
                logger.error(f'앨범 이미지 URL 업데이트 실패: {album.album_id}, 오류: {e}')
                stats['failed'] += 1
                stats['processed'] += 1
        
        return stats
