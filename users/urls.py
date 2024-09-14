from django.urls import path
from .views import (
    IssueCompleteView, 
    IssueListCreateView, 
    IssueRetrieveView, 
    IssueDeleteView,
    IssueLikeView,
    LikedIssuesListView,
    RegisterView, 
    LoginView, 
    UserListView,
    UserDeleteView,
    UserDetailView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:user_id>/delete/', UserDeleteView.as_view(), name='user-delete'),
    path('issue/create/', IssueListCreateView.as_view(), name='create_issue'),
    path('issue/<int:pk>/complete/', IssueCompleteView.as_view(), name='complete_issue'),
    path('issue/<int:issue_id>/delete/', IssueDeleteView.as_view(), name='issue-delete'),
    path('issue/<int:issue_id>/like/', IssueLikeView.as_view(), name='issue-like'),
    path('issues/liked/', LikedIssuesListView.as_view(), name='liked-issues'),
    path('issue/all/', IssueRetrieveView.as_view(), name="issue-retrieval"),
    path('issue/<int:issue_id>/', IssueRetrieveView.as_view(), name="issue-detail"),  # New endpoint
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
