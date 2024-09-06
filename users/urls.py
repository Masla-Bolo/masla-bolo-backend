from django.urls import path
from .views import IssueCompleteView, IssueListCreateView, IssueRetrieveView, RegisterView, LoginView, UserView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('users/', UserView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserView.as_view(), name='user-detail'),
    path('issue/create/', IssueListCreateView.as_view(), name='create_issue'),
    path('issue/complete/<int:pk>', IssueCompleteView.as_view(), name='complete_issue'),
    path('issue/list/', IssueRetrieveView.as_view(), name="issue-retrieval"),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
