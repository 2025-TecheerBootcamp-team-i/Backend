"""
차트 조회 관련 Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from django.utils.timezone import localtime

from ..models import Charts
from ..serializers import ChartItemSerializer, ChartResponseSerializer


class ChartView(APIView):
    """
    차트 조회 API
    - GET: 지정한 타입의 최신 차트 조회
    """
    
    # 유효한 차트 타입
    VALID_TYPES = ['realtime', 'daily', 'ai']
    
    @extend_schema(
        summary="차트 조회",
        description="""
지정한 타입의 최신 차트를 조회합니다.

**차트 타입:**
- `realtime`: 실시간 차트 (10분마다 갱신, 최근 3시간 집계)
- `daily`: 일일 차트 (매일 자정 갱신, 전날 전체 집계)
- `ai`: AI 차트 (매일 자정 갱신, AI 곡만 집계)

**응답:**
- 순위, 재생 횟수, 음악 정보 포함
- 최대 100개 항목

**순위 변동 계산:**
- 이전 차트와 비교하여 순위 변동 계산
- 순위 변동 포함 (이전 순위 - 현재 순위= 양수=상승, 음수=하락, 0=유지)
        """,
        parameters=[
            OpenApiParameter(
                name='type',
                type=str,
                location=OpenApiParameter.PATH,
                description='차트 타입 (realtime|daily|ai)',
                required=True,
                examples=[
                    OpenApiExample(
                        name='실시간 차트',
                        value='realtime',
                        description='실시간 차트 조회'
                    ),
                    OpenApiExample(
                        name='일일 차트',
                        value='daily',
                        description='일일 차트 조회'
                    ),
                    OpenApiExample(
                        name='AI 차트',
                        value='ai',
                        description='AI 곡 차트 조회'
                    ),
                ]
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=ChartResponseSerializer,
                description="차트 조회 성공",
                examples=[
                    OpenApiExample(
                        name="성공 응답",
                        value={
                            "type": "realtime",
                            "generated_at": "2026-01-13T15:30:00Z",
                            "total_count": 100,
                            "items": [
                                {
                                    "rank": 1,
                                    "play_count": 1500,
                                    "music": {
                                        "music_id": 123,
                                        "music_name": "인기곡 1",
                                        "artist": {"artist_name": "아티스트1"},
                                        "album": {"album_name": "앨범1"},
                                        "genre": "Pop",
                                        "duration": 210,
                                        "is_ai": False,
                                        "audio_url": "https://...",
                                        "itunes_id": 123456789
                                    }
                                }
                            ]
                        }
                    )
                ]
            ),
            400: OpenApiResponse(description="잘못된 차트 타입"),
            404: OpenApiResponse(description="차트 데이터 없음"),
        },
        tags=["차트"]
    )
    def get(self, request, type):
        """차트 조회 (순위 변동 동적 계산)"""
        # 1. 타입 검증
        if type not in self.VALID_TYPES:
            return Response(
                {
                    "detail": f"잘못된 차트 타입입니다. 가능한 값: {', '.join(self.VALID_TYPES)}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. 최신 차트 날짜 조회
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        latest_chart = Charts.objects.filter(type=type).order_by('-chart_date').first()
        
        if not latest_chart:
            return Response(
                {"detail": f"'{type}' 차트 데이터가 없습니다"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 3. 현재 차트 조회
        # DB가 timestamp(timezone 없음)이므로 날짜+시간 문자열로 비교
        chart_items = Charts.objects.filter(
            type=type,
            music__is_deleted=False  # 삭제된 음악 제외
        ).extra(
            where=["chart_date::text = %s::text"],
            params=[str(latest_chart.chart_date)]
        ).select_related(
            'music',
            'music__artist',
            'music__album'
        ).order_by('rank')
        
        # 4. 이전 차트 조회 (순위 변동 계산용)
        previous_chart = Charts.objects.filter(
            type=type,
            chart_date__lt=latest_chart.chart_date,
            is_deleted=False
        ).order_by('-chart_date').first()
        
        previous_ranks = {}
        if previous_chart:
            # 이전 차트의 순위 정보를 {music_id: rank} 딕셔너리로 구성
            previous_items = Charts.objects.filter(
                type=type,
                music__is_deleted=False  # 삭제된 음악 제외
            ).extra(
                where=["chart_date::text = %s::text"],
                params=[str(previous_chart.chart_date)]
            ).values('music_id', 'rank')

            previous_ranks = {item['music_id']: item['rank'] for item in previous_items}
        
        # 5. 각 차트 항목에 rank_change 추가
        for chart in chart_items:
            if chart.music_id in previous_ranks:
                # 이전 순위 - 현재 순위 (양수=상승, 음수=하락, 0=유지)
                chart.rank_change = previous_ranks[chart.music_id] - chart.rank
            else:
                # 이전 차트에 없었음 (신규 진입)
                chart.rank_change = None
        
        # 6. 응답 구성
        response_data = {
            "type": type,
            "generated_at": latest_chart.chart_date,
            "total_count": chart_items.count(),
            "items": ChartItemSerializer(chart_items, many=True).data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
