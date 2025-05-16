from .common import MyApiUser, Point, serializers


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    latitude = serializers.DecimalField(
        write_only=True, required=True, max_digits=13, decimal_places=10
    )
    longitude = serializers.DecimalField(
        write_only=True, required=True, max_digits=13, decimal_places=10
    )
    profile_image = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = MyApiUser
        fields = [
            "id",
            "email",
            "username",
            "password",
            "role",
            "profile_image",
            "latitude",
            "longitude",
        ]

    def create(self, validated_data: dict):
        role = validated_data.get("role", "user")
        longitude = float(validated_data["longitude"])
        latitude = float(validated_data["latitude"])
        location = Point(longitude, latitude)

        if role == "admin":
            user = MyApiUser.objects.create_superuser(
                email=validated_data["email"],
                username=validated_data["username"],
                password=validated_data["password"],
                location=location,
            )
        else:  # in case of official and user registration will be same!
            user = MyApiUser.objects.create_user(
                email=validated_data["email"],
                username=validated_data["username"],
                password=validated_data["password"],
                location=location,
                role=role,
            )
        if "profile_image" in validated_data:
            user.profile_image = validated_data["profile_image"]
            user.save()

        return user
