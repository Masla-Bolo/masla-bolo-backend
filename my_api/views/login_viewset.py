from .common import (LoginSerializer, generics, StandardResponseMixin, MyApiUserSerializer,
                             RefreshToken, status, MyApiUser,update_last_login)

class LoginView(generics.GenericAPIView, StandardResponseMixin):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        role = request.data.get("role")

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            if user.role == role:
                refresh = RefreshToken.for_user(user)
                user_data = MyApiUserSerializer(user).data

                if not user.verified and user.role == MyApiUser.USER:
                    return self.success_response(
                        message="Email Not Verified!",
                        data={"user": user_data},
                        status_code=status.HTTP_200_OK,
                    )

                update_last_login(None, user)

                return self.success_response(
                    message="Login Successful!",
                    data={"token": str(refresh.access_token), "user": user_data},
                    status_code=status.HTTP_200_OK,
                )

        return self.error_response(
            message="Incorrect Credentials",
            data={"VerificationError"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )