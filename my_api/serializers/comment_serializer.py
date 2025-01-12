from .common import serializers, Comment, OuterRef, Prefetch, Count, Exists, Like

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
        fields = [
            "id",
            "user",
            "issue",
            "parent",
            "content",
            "created_at",
            "updated_at",
            "likes_count",
            "is_edited",
            "replies",
            "is_liked",
            "reply_to",
        ]
        read_only_fields = [
            "user",
            "issue",
            "created_at",
            "updated_at",
            "likes_count",
            "is_edited",
            "is_liked",
        ]

    def get_user(self, obj: Comment) -> dict:
        return {
            "id": obj.user.id,
            "username": obj.user.username,
            "role": obj.user.role,
            "profile_image": obj.user.profile_image,
        }

    def get_is_liked(self, obj: Comment):
        return getattr(obj, "is_liked", False)

    def create(self, validated_data: dict):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    @classmethod
    def setup_eager_loading(cls, queryset, request):
        likes_subquery = Like.objects.filter(user=request.user, comment=OuterRef("pk"))

        # Prefetch replies for multiple levels (nested replies)
        replies_queryset = Comment.objects.select_related("user").prefetch_related(
            Prefetch("replies", queryset=Comment.objects.select_related("user"))
        )

        queryset = (
            queryset.select_related("user", "issue", "parent", "reply_to")
            .prefetch_related(Prefetch("replies", queryset=replies_queryset))
            .annotate(replies_count=Count("replies"), is_liked=Exists(likes_subquery))
        )

        return queryset