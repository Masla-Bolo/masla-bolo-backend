# from datetime import timezone
from rest_framework import serializers
from .models import MyApiUser, Issue, Like, Comment, MyApiOfficial
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Exists, OuterRef, Count, Prefetch
from django.contrib.gis.geos import Point

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    latitude = serializers.DecimalField(write_only=True, required=True, max_digits=13, decimal_places=10)
    longitude = serializers.DecimalField(write_only=True, required=True, max_digits=13, decimal_places=10)
    profile_image = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = MyApiUser
        fields = ["id", "email", "username", "password", "role", "profile_image", "latitude", "longitude"]

    def create(self, validated_data: dict):
        role = validated_data.get('role', 'user')
        longitude = float(validated_data["longitude"])
        latitude = float(validated_data["latitude"])
        location = Point(longitude, latitude)

        if role == "admin":
            user = MyApiUser.objects.create_superuser(
                email=validated_data['email'],
                username=validated_data['username'],
                password=validated_data['password'],
                location=location
            )
        else:  # in case of official and user registration will be same!
            user = MyApiUser.objects.create_user(
                email=validated_data['email'],
                username=validated_data['username'],
                password=validated_data['password'],
                location=location,
                role=role,
            )
        if 'profile_image' in validated_data:
            user.profile_image = validated_data['profile_image']
            user.save()

        return user


class OfficialSerializer(serializers.ModelSerializer):

    class Meta:
        model = MyApiOfficial
        fields = [
            'id', 'user', 'assigned_issues', 'area_range', 
            'city_name', 'country_name', 'district_name', 'country_code'
        ]
        read_only_fields = ['area_range', 'country_code']

class SocialRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ["id", "email", "username", "role", "profile_image", "is_social"]

    def create(self, validated_data):
        role = validated_data.get('role', 'user')

        user = MyApiUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            role=role,
            verified=True,
            verification_code=None,
            code_expiry=None,
            is_social=True,
        )
        if 'profile_image' in validated_data:
            user.profile_image = validated_data['profile_image']
            user.save()

        return user

class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

    def validate(self, data: dict):
        email = data.get('email')
        code = data.get('code')

        try:
            user = MyApiUser.objects.get(email=email)
        except MyApiUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        if user.verification_code != code:
            raise serializers.ValidationError("Invalid verification code.")
        
        if user.code_expiry < timezone.now():
            raise serializers.ValidationError("Verification code has expired.")
        
        data['user'] = user
        return data

    def save(self):
        email = self.validated_data['email']
        user = MyApiUser.objects.get(email=email)
        user.verified = True
        user.verification_code = None
        user.code_expiry = None
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data: dict):
        email = data.get("email")
        password = data.get("password")
        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError("Invalid login credentials")
        
        # Return the user instance
        return {'user': user}

class MyApiUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ['id', 'email', 'username', "role", 'is_active', 'profile_image','created_at', 'updated_at', "verified"]  # Include the new fields

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
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'issue', 'parent', 'content', 'created_at', 'updated_at', 'likes_count', 'is_edited', 'replies', 'is_liked', 'reply_to']
        read_only_fields = ['user', 'issue', 'created_at', 'updated_at', 'likes_count', 'is_edited', 'is_liked']

    def get_user(self, obj: Comment) -> dict:
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'role': obj.user.role,
            'profile_image': obj.user.profile_image
        }

    def get_is_liked(self, obj: Comment):
        return getattr(obj, 'is_liked', False)

    def create(self, validated_data: dict):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    @classmethod
    def setup_eager_loading(cls, queryset, request):
        likes_subquery = Like.objects.filter(user=request.user, comment=OuterRef('pk'))
        
        # Prefetch replies for multiple levels (nested replies)
        replies_queryset = Comment.objects.select_related('user').prefetch_related(
            Prefetch('replies', queryset=Comment.objects.select_related('user'))
        )
        
        queryset = queryset.select_related('user', 'issue', 'parent', 'reply_to').prefetch_related(
            Prefetch('replies', queryset=replies_queryset)
        ).annotate(
            replies_count=Count('replies'),
            is_liked=Exists(likes_subquery)
        )

        return queryset

class IssueSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    class Meta:
        model = Issue
        fields = ['id', 'title', 'user', 
                  'latitude', 'longitude', 
                  'description', 'categories', 'images', 'issue_status', 'is_anonymous', "likes_count", "comments_count", "is_liked", 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at', 'comments_count']

    def to_representation(self, obj: Issue):
        representation = super().to_representation(obj)
        representation['latitude'] = round(float(representation['latitude']), 12)
        representation['longitude'] = round(float(representation['longitude']), 12)
        return representation
    
    def get_user(self, obj: Issue) -> dict: 
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            "role": obj.user.role,
            "profile_image": obj.user.profile_image
        }

    def get_is_liked(self, obj):
        user = self.context['request'].user
        return getattr(obj, 'is_liked', False)

    @classmethod
    def setup_eager_loading(cls, queryset, user):
        # Prefetch related objects
        queryset = queryset.select_related('user')
        
        # Annotate is_liked
        like_exists = Exists(Like.objects.filter(user=user, issue=OuterRef('pk')))
        queryset = queryset.annotate(is_liked=like_exists)
        
        return queryset

