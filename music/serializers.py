from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Users

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)
    
    class Meta:
        model = Users
        fields = ['email', 'password', 'nickname']
    
    def create(self, validated_data):
        # 비밀번호 해싱
        validated_data['password'] = make_password(validated_data['password'])
        return Users.objects.create(**validated_data)

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)