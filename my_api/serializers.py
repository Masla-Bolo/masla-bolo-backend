from rest_framework import serializers
from .models import MyApiUser, Issue, Like, Comment
from django.contrib.auth import authenticate

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = MyApiUser
        fields = ["id", 'email', "username", 'password', 'role']

    def create(self, validated_data):
        if validated_data['role'] == "admin":
            user = MyApiUser.objects.create_superuser(
                email=validated_data['email'],
                username=validated_data['username'],
                password=validated_data['password'],
            )
            return user
        else:
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
        
        # Return the user instance
        return {'user': user}

# Serializer for listing user details
class MyApiUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ['id', 'email', 'username', "role", 'is_active', 'created_at', 'updated_at']  # Include the new fields

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['user', 'issue', "comment", 'created_at']
        read_only_fields = ['created_at']

class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    replies = RecursiveSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'issue', 'parent', 'content', 'created_at', 'updated_at', 'likes_count', 'is_edited', 'replies', 'is_liked']
        read_only_fields = ['user', 'issue', 'created_at', 'updated_at', 'likes_count', 'is_edited']

    # will get the user data needed and should be the same name as the 'user' variable
    # future enhancements: profile pic
    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'role': obj.user.role
        }

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(user=request.user, comment=obj).exists()
        return False

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class IssueSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    user=MyApiUserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = ['id', 'title', 'user', 'latitude', 'longitude', 'description', 'categories', 'images', 'issue_status', 'is_anonymous', "likes_count", "comments", "comments_count", 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at', 'comments_count'] # can't be updated via api
    

    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if 'comments' in representation:
            representation.pop('comments')
        return representation
