from .common import Exists, Issue, Like, OuterRef, serializers
from django.core.validators import MinLengthValidator
from rest_framework.exceptions import ValidationError


class IssueSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    title = serializers.CharField(
        validators=[MinLengthValidator(5, message="Title must be at least 5 characters long")]
    )
    description = serializers.CharField(
        validators=[MinLengthValidator(10, message="Description must be at least 10 characters long")]
    )

    class Meta:
        model = Issue
        fields = [
            "id",
            "title",
            "user",
            "location",
            "description",
            "categories",
            "images",
            "issue_status",
            "is_anonymous",
            "likes_count",
            "comments_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at", "comments_count"]

    def get_user(self, obj: Issue) -> dict:
        return {
            "id": obj.user.id,
            "username": obj.user.username,
            "role": obj.user.role,
            "profile_image": obj.user.profile_image,
        }

    def get_is_liked(self, obj):
        user = self.context["request"].user
        return getattr(obj, "is_liked", False)

    @classmethod
    def setup_eager_loading(cls, queryset, user):

        queryset = queryset.select_related("user")

        like_exists = Exists(Like.objects.filter(user=user, issue=OuterRef("pk")))
        queryset = queryset.annotate(is_liked=like_exists)

        return queryset

    def validate_categories(self, value):
        if not value or not isinstance(value, list):
            raise ValidationError("Categories must be a non-empty list")
        
        valid_categories = [choice[1] for choice in Issue.CATEGORY_CHOICES]
        invalid_categories = [cat for cat in value if cat not in valid_categories]
        # print(invalid_categories, valid_categories)
        
        if invalid_categories:
            raise ValidationError(f"Invalid categories: {', '.join(invalid_categories)}")
        
        return value

    def validate_location(self, value):
        if not value:
            raise ValidationError("Location is required")
        return value

    def validate_images(self, value):
        if not isinstance(value, list):
            raise ValidationError("Images must be a list")
        
        if len(value) > 5:
            raise ValidationError("Maximum 5 images allowed")
            
        return value
