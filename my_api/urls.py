from django.urls import include, path

from my_api.views import (
    CommentViewSet,
    IssueViewSet,
    LoginView,
    NotificationViewSet,
    OfficialViewSet,
    RegisterView,
    SendEmailView,
    SocialRegisterView,
    UserViewSet,
    VerifyEmailView,
)

from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

router = routers.DefaultRouter()
router.register(r"issues", IssueViewSet, basename="issues")
router.register(r"users", UserViewSet, basename="users")
router.register(r"comments", CommentViewSet, basename="comments")
router.register(r"officials", OfficialViewSet, basename="officials")
router.register(r"notifications", NotificationViewSet, basename="notifications")

urlpatterns = [
    path("", include(router.urls)),
    path("register/", RegisterView.as_view(), name="register"),
    path("social-register/", SocialRegisterView.as_view(), name="social-register"),
    path("login/", LoginView.as_view(), name="login"),
    path("send-email-verification/", SendEmailView.as_view(), name="send-email"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
