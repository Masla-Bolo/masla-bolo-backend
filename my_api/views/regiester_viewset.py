from .common import (
    MyApiUser,
    RefreshToken,
    RegisterSerializer,
    SocialRegisterSerializer,
    StandardResponseMixin,
    generics,
    status,
    APIView,
    timezone,
    timedelta,
    random,
    VerifyEmailSerializer,
    MyApiUserSerializer,
    update_last_login,
    render_to_string,
    EmailMultiAlternatives,
    Response,
    settings

)

class RegisterView(generics.CreateAPIView, StandardResponseMixin):
    queryset = MyApiUser.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(verified=False)

        if user.role == "user":
            return self.success_response(
                message="Account Registered Successfully!!",
                data={"email": user.email},
                status_code=status.HTTP_200_OK,
            )
        else:
            refresh = RefreshToken.for_user(user)
            user_data = RegisterSerializer(user).data
            return self.success_response(
                message="Account Registered Successfully!!",
                data={"token": str(refresh.access_token), "user": user_data},
                status_code=status.HTTP_200_OK,
            )


class SocialRegisterView(generics.CreateAPIView, StandardResponseMixin):
    queryset = MyApiUser.objects.all()
    serializer_class = SocialRegisterSerializer

    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        user = MyApiUser.objects.filter(email=email)

        if user or not user.is_social:
            return self.error_response(
                message="User with this email already exists!",
                data={},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # existing_user = MyApiUser.objects.filter(email=email, is_social=True).first()
        if user.is_social:
            refresh = RefreshToken.for_user(user)
            return self.success_response(
                message="User already exists, returning existing user.",
                data={
                    "token": str(refresh.access_token),
                    "user": SocialRegisterSerializer(user).data,
                },
                status_code=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(verified=True)

        refresh = RefreshToken.for_user(user)
        return self.success_response(
            message="Account Registered Successfully!",
            data={"token": str(refresh.access_token), "user": serializer.data},
            status_code=status.HTTP_200_OK,
        )


class SendEmailView(APIView, StandardResponseMixin):
    def get(self, request, refresh_code=False):
        email = self.request.query_params.get("email")
        # print(email)
        user = MyApiUser.objects.get(email=email)
        # print(user)

        if user.verified:
            self.error_response(
                message="Email is Already Verified. Try Logging in.",
                data="AccountExists",
                status_code=status.HTTP_100_CONTINUE,
            )
        verification_code = str(random.randint(100000, 999999))

        user.verification_code = verification_code
        user.code_expiry = timezone.now() + timedelta(minutes=5)
        user.save()

        email_subject = "Verify your email"
        email_body_html = render_to_string(
            "emails/email_verification_template.html",
            {"username": user.username, "verification_code": verification_code},
        )

        email = EmailMultiAlternatives(
            email_subject, email_body_html, settings.EMAIL_HOST_USER, [user.email]
        )
        email.attach_alternative(email_body_html, "text/html")
        email.send()
        return self.success_response(
            message="Verification Email Sent Successfully!",
            data={"email": user.email},
            status_code=status.HTTP_200_OK,
        )


class VerifyEmailView(APIView, StandardResponseMixin):
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user = serializer.validated_data["user"]
            update_last_login(None, user)

            refresh = RefreshToken.for_user(user)
            user_data = MyApiUserSerializer(user).data

            return self.success_response(
                message="Email verified successfully!",
                data={"token": str(refresh.access_token), "user": user_data},
                status_code=status.HTTP_200_OK,
            )
        return self.error_response(message="Serializer Not Valid", data=serializer.data, status_code=status.HTTP_400_BAD_REQUEST)