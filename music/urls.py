from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView

app_name = 'music'

urlpatterns = [
    path('auth/users/', RegisterView.as_view(), name='register'),
    path('auth/tokens/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]