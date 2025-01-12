from .common import serializers, Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["user", "title", "description", "created_at", "screen", "screen_id"]
        read_only_fields = ["created_at"]