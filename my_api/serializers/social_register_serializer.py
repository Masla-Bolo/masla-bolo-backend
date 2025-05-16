from .common import MyApiUser, serializers


class SocialRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ["id", "email", "username", "role", "profile_image", "is_social"]

    def create(self, validated_data):
        role = validated_data.get("role", "user")

        user = MyApiUser.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            role=role,
            verified=True,
            verification_code=None,
            code_expiry=None,
            is_social=True,
        )
        if "profile_image" in validated_data:
            user.profile_image = validated_data["profile_image"]
            user.save()

        return user
