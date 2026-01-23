"""
OpenSearch 인덱스 설정 및 데이터 동기화 명령어

사용법:
    python manage.py opensearch_setup --create       # 인덱스 생성
    python manage.py opensearch_setup --delete       # 인덱스 삭제
    python manage.py opensearch_setup --sync         # DB 데이터 동기화
    python manage.py opensearch_setup --reset        # 삭제 후 생성 및 동기화
"""
from django.core.management.base import BaseCommand
from music.services.opensearch import opensearch_service
from music.models import Music


class Command(BaseCommand):
    help = 'OpenSearch 인덱스 관리 및 데이터 동기화'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create',
            action='store_true',
            help='OpenSearch 인덱스 생성',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='OpenSearch 인덱스 삭제',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='DB 데이터를 OpenSearch에 동기화',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='인덱스 삭제 후 재생성 및 동기화',
        )

    def handle(self, *args, **options):
        # OpenSearch 사용 가능 여부 확인
        if not opensearch_service.is_available():
            self.stdout.write(
                self.style.ERROR('OpenSearch에 연결할 수 없습니다.')
            )
            self.stdout.write(
                self.style.WARNING('OPENSEARCH_HOST 환경 변수를 확인하세요.')
            )
            return

        # 리셋 옵션
        if options['reset']:
            self.stdout.write('OpenSearch 인덱스를 리셋합니다...')
            
            # 인덱스 삭제
            if opensearch_service.delete_index():
                self.stdout.write(
                    self.style.SUCCESS('✓ 인덱스 삭제 완료')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('인덱스가 존재하지 않거나 삭제할 수 없습니다.')
                )
            
            # 인덱스 생성
            if opensearch_service.create_index():
                self.stdout.write(
                    self.style.SUCCESS('✓ 인덱스 생성 완료')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ 인덱스 생성 실패')
                )
                return
            
            # 데이터 동기화
            self._sync_data()
            return

        # 인덱스 생성
        if options['create']:
            self.stdout.write('OpenSearch 인덱스를 생성합니다...')
            if opensearch_service.create_index():
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ 인덱스 생성 완료: {opensearch_service.index_name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ 인덱스 생성 실패')
                )

        # 인덱스 삭제
        if options['delete']:
            self.stdout.write(
                self.style.WARNING('OpenSearch 인덱스를 삭제합니다...')
            )
            if opensearch_service.delete_index():
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ 인덱스 삭제 완료: {opensearch_service.index_name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('인덱스가 존재하지 않거나 삭제할 수 없습니다.')
                )

        # 데이터 동기화
        if options['sync']:
            self._sync_data()

        # 옵션이 없으면 도움말 출력
        if not any([options['create'], options['delete'], options['sync'], options['reset']]):
            self.stdout.write(
                self.style.WARNING('옵션을 선택하세요: --create, --delete, --sync, --reset')
            )

    def _sync_data(self):
        """DB 데이터를 OpenSearch에 동기화"""
        self.stdout.write('DB 데이터를 OpenSearch에 동기화합니다...')
        
        # DB에서 모든 음악 조회
        musics = Music.objects.select_related(
            'artist', 'album'
        ).prefetch_related('music_tags__tag')
        
        total_count = musics.count()
        self.stdout.write(f'총 {total_count}개의 음악을 동기화합니다...')
        
        music_list = []
        for music in musics:
            # 태그 추출
            tags = [mt.tag.tag_key for mt in music.music_tags.all() if mt.tag]
            
            music_data = {
                'music_id': music.music_id,
                'itunes_id': music.itunes_id,
                'music_name': music.music_name or '',
                'artist_name': music.artist.artist_name if music.artist else '',
                'artist_id': music.artist.artist_id if music.artist else None,
                'album_name': music.album.album_name if music.album else '',
                'album_id': music.album.album_id if music.album else None,
                'genre': music.genre or '',
                'duration': music.duration or 0,
                'is_ai': getattr(music, 'is_ai', False),
                'tags': tags,
                'lyrics': music.lyrics or '',  # 가사 추가
                'created_at': music.created_at.isoformat() if music.created_at else None,
                'play_count': 0,  # TODO: 재생 수 통계 추가
                'like_count': 0,  # TODO: 좋아요 수 통계 추가
            }
            music_list.append(music_data)
        
        # 일괄 인덱싱
        indexed_count = opensearch_service.bulk_index_music(music_list)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ 동기화 완료: {indexed_count}/{total_count}개 인덱싱됨'
            )
        )
