from .common import MyApiUser, serializers, Point


class SocialRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyApiUser
        fields = ["id", "email", "username", "role", "profile_image", "is_social", "location"]

    def create(self, validated_data):
        role = validated_data.get("role", "user")
        longitude = float(validated_data['location']["longitude"])
        latitude = float(validated_data['location']["latitude"])
        location = Point(longitude, latitude)

        user = MyApiUser.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            location=location,
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
