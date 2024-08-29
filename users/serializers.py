from rest_framework import serializers
from .models import MyApiUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ['id', 'username', 'password', 'email']