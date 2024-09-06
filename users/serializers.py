from rest_framework import serializers
from .models import MyApiUser, Issue
from django.contrib.auth import authenticate

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ["id", 'email', "username", 'password', 'role']

    def create(self, validated_data):
        user = MyApiUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            role=validated_data['role']
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        user = authenticate(username=email, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid login credentials")
        return data

# Serializer for listing user details
class MyApiUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ['id', 'email', 'username', "role", 'is_active']  # Adjust fields as necessary

class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = ['id', 'title', 'user', 'latitude', 'longitude', 'description', 'categories', 'images', 'issue_status']
        read_only_fields = ['user']  # Prevent the user from being changed once set
