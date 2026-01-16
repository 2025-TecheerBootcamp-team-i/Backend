"""
core 프로젝트의 메인 URL 설정 파일
"""
from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # 루트 URL을 /music/list/로 리다이렉트
    path('', RedirectView.as_view(url=reverse_lazy('music:music_list_page')), name='root-redirect'),
    path('admin/', admin.site.urls),
     # 웹 페이지 (UI)
    path('music/', include('music.urls')),
    # Music API
    path('api/v1/', include('music.urls')),
    # API 엔드포인트
    path('api/music/', include('music.urls')),
    # Swagger/OpenAPI 문서
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),  # OpenAPI 스키마 JSON
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # Swagger UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),  # ReDoc UI
    # Prometheus 메트릭 엔드포인트
    path('metrics/', include('django_prometheus.urls')),  # /metrics/ 엔드포인트
]


# 개발 환경(DEBUG=True)에서 정적 파일(CSS, JS, 이미지) 및 미디어 파일을 서빙하기 위한 설정입니다.
# 프로덕션 환경에서는 웹 서버(Nginx, Traefik 등)가 직접 정적 파일을 서빙해야 합니다.
if settings.DEBUG:
    # 정적 파일 서빙 (CSS, JavaScript, 이미지 등)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # 미디어 파일 서빙 (사용자가 업로드한 파일)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)