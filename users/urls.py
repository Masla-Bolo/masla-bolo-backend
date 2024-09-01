from django.urls import path
from .views import RegisterView, LoginView, UserView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('users/', UserView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserView.as_view(), name='user-detail'),
    # path('users/create/', create_user, name='create_user'),
    # path('users/<int:user_id>/update/', update_user, name='update_user'),
    # path('users/<int:user_id>/delete/', delete_user, name='delete_user'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]