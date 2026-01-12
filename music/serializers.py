"""
인증 관련 Serializer
사용자 회원가입 및 로그인 데이터 검증 및 변환
"""
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Users


class UserRegisterSerializer(serializers.ModelSerializer):
    """회원가입 Serializer - 이메일, 비밀번호, 닉네임 입력받아 사용자 생성"""
    password = serializers.CharField(write_only=True, min_length=4)
    
    class Meta:
        model = Users
        fields = ['email', 'password', 'nickname']
    
    def create(self, validated_data):
        """비밀번호 해싱 후 사용자 생성"""
        validated_data['password'] = make_password(validated_data['password'])
        return Users.objects.create(**validated_data)


class UserLoginSerializer(serializers.Serializer):
    """로그인 Serializer - 이메일, 비밀번호 입력 검증"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)