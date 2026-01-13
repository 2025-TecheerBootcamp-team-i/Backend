"""
인증 관련 Serializer
사용자 회원가입 및 로그인 데이터 검증 및 변환
"""
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone  # 타임스탬프 자동 설정을 위해 추가
from .models import Users


class UserRegisterSerializer(serializers.ModelSerializer):
    """회원가입 Serializer - 이메일, 비밀번호, 닉네임 입력받아 사용자 생성"""
    password = serializers.CharField(write_only=True, min_length=4)
    
    class Meta:
        model = Users
        fields = ['email', 'password', 'nickname']
    
    def create(self, validated_data):
        """비밀번호 해싱 후 사용자 생성"""
        # 비밀번호를 해시값으로 변환 (보안)
        validated_data['password'] = make_password(validated_data['password'])
        
        # 타임스탬프 및 삭제 플래그 자동 설정
        # Users 모델이 managed=False로 설정되어 있어 auto_now_add/auto_now가 작동하지 않음
        # 따라서 수동으로 값을 설정해야 함
        validated_data['created_at'] = timezone.now()  # 생성 시간
        validated_data['updated_at'] = timezone.now()  # 수정 시간 (생성 시에는 created_at과 동일)
        validated_data['is_deleted'] = False  # 삭제 플래그 (기본값: False)
        
        return Users.objects.create(**validated_data)


class UserLoginSerializer(serializers.Serializer):
    """로그인 Serializer - 이메일, 비밀번호 입력 검증"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)