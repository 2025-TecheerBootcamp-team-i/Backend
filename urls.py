"""
core 프로젝트의 메인 URL 설정 파일
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # 웹 페이지 (UI)
    path('music/', include('music.urls')),
    # API 엔드포인트
    path('api/music/', include('music.urls')),
]

# 개발 환경(DEBUG=True)에서 사용자가 업로드한 미디어 파일을 서빙하기 위한 설정입니다.
# 프로덕션 환경에서는 웹 서버(Nginx, Traefik 등)가 직접 미디어 파일을 서빙해야 합니다.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)