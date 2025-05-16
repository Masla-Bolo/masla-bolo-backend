from .common import MyApiUser, serializers


class MyApiUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = [
            "id",
            "email",
            "username",
            "role",
            "is_active",
            "profile_image",
            "created_at",
            "updated_at",
            "verified",
            "location",
        ]
