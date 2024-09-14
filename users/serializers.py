from rest_framework import serializers
from .models import MyApiUser, Issue
from django.contrib.auth import authenticate

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

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
        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError("Invalid login credentials")
        
        # Return the user instance, not the raw data
        return {'user': user}

# Serializer for listing user details
class MyApiUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ['id', 'email', 'username', "role", 'is_active', 'created_at', 'updated_at']  # Include the new fields

class IssueSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        model = Issue
        fields = ['id', 'title', 'user', 'latitude', 'longitude', 'description', 'categories', 'images', 'issue_status', 'is_anonymous', "likes_count", 'created_at', 'updated_at']  # Include the new fields
        read_only_fields = ['user', 'created_at', 'updated_at']  # Ensure these fields are read-only
