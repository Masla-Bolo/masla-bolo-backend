from .common import Exists, Issue, Like, OuterRef, serializers


class IssueSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

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
