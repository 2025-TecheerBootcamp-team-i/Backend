"""
인증 관련 Serializers - 회원가입, 로그인
"""
import re
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from ..models import Users


class UserRegisterSerializer(serializers.ModelSerializer):
    """회원가입 Serializer - 이메일, 비밀번호, 닉네임 입력받아 사용자 생성"""
    password = serializers.CharField(write_only=True, min_length=8, max_length=16)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = Users
        fields = ['email', 'password', 'password_confirm', 'nickname']

    def validate_email(self, value):
        """이메일 형식 및 중복 검증"""
        # 이메일 형식 검증 (정규식)
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError("이메일 형식이 올바르지 않습니다")

        # 중복 확인
        if Users.objects.filter(email=value).exists():
            raise serializers.ValidationError("이미 사용중인 이메일입니다")

        return value

    def validate_password(self, value):
        """비밀번호 복잡도 검증"""
        missing = []

        if not re.search(r'[A-Za-z]', value):
            missing.append('영문자')
        if not re.search(r'\d', value):
            missing.append('숫자')
        if not re.search(r'[!@#$%^&*()_+\-=\\[\]{}|;:\'",.<>/?~]', value):
            missing.append('특수기호')

        if missing:
            raise serializers.ValidationError(f"문자/숫자/특수기호가 부족해요: {', '.join(missing)}")

        return value

    def validate(self, data):
        """전체 데이터 검증"""
        # 비밀번호 확인 검증
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': "비밀번호가 일치하지 않습니다"
            })

        # 공백 필드 검증
        for field in ['email', 'password', 'nickname']:
            if not data.get(field) or not data.get(field).strip():
                raise serializers.ValidationError(f"{field}은(는) 필수 입력 항목입니다")

        return data

    def create(self, validated_data):
        """비밀번호 해싱 후 사용자 생성"""
        # 저장 시 password_confirm 제외
        validated_data.pop('password_confirm', None)

        # 비밀번호를 해시값으로 변환 (보안)
        validated_data['password'] = make_password(validated_data['password'])

        # 타임스탬프 및 삭제 플래그 자동 설정
        # Users 모델이 managed=False로 설정되어 있어 auto_now_add/auto_now가 작동하지 않음
        validated_data['created_at'] = timezone.now()
        validated_data['updated_at'] = timezone.now()
        validated_data['is_deleted'] = False

        return Users.objects.create(**validated_data)


class UserLoginSerializer(serializers.Serializer):
    """로그인 Serializer - 이메일, 비밀번호 입력 검증"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
