from .common import MyApiUser, serializers, timezone


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

    def validate(self, data: dict):
        email = data.get("email")
        code = data.get("code")

        try:
            user = MyApiUser.objects.get(email=email)
        except MyApiUser.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        if user.verification_code != code:
            raise serializers.ValidationError("Invalid verification code.")

        if user.code_expiry < timezone.now():
            raise serializers.ValidationError("Verification code has expired.")

        data["user"] = user
        return data

    def save(self):
        email = self.validated_data["email"]
        user = MyApiUser.objects.get(email=email)
        user.verified = True
        user.verification_code = None
        user.code_expiry = None
        user.save()
        return user
