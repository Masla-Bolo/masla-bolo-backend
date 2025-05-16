from .common import Like, serializers


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ["user", "issue", "comment", "created_at"]
        read_only_fields = ["created_at"]
