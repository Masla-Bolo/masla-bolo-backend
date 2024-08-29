from django.urls import path
from .views import CustomLoginView, create_user, register_user, update_user, delete_user, get_users

urlpatterns = [
    path('users/', get_users, name='get_users'),
    # path('users/create/', create_user, name='create_user'),
    path('users/<int:user_id>/update/', update_user, name='update_user'),
    path('users/<int:user_id>/delete/', delete_user, name='delete_user'),
    path('users/register/', register_user, name='register_user'),
    path('users/login/', CustomLoginView.as_view(), name='login'),
]