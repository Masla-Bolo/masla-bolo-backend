from my_api import views
from django.urls import include, path
from .views import (
    RegisterView, 
    LoginView,
)
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r"issues", views.IssueViewSet, basename="issues")
router.register(r"users", views.UserViewSet, basename="users")
router.register(r"comments", views.CommentViewSet, basename="comments")

urlpatterns = [
    path("", include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]