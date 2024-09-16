from django.urls import path
from .views import (
    CommentCreateView,
    CommentDeleteView,
    CommentLikeView,
    IssueCommentsListView,
    IssueCompleteView, 
    IssueListCreateView, 
    IssueRetrieveView, 
    IssueDeleteView,
    IssueLikeView,
    LikedCommentsListView,
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
    path('users/delete/<int:user_id>/', UserDeleteView.as_view(), name='user-delete'),
    path('issues/', IssueListCreateView.as_view(), name='create_issue'),
    path('issues/complete/<int:pk>/', IssueCompleteView.as_view(), name='complete_issue'),
    path('issues/delete/<int:issue_id>/', IssueDeleteView.as_view(), name='issue-delete'),
    path('issues/like/<int:issue_id>/', IssueLikeView.as_view(), name='issue-like'),
    path('issues/liked/', LikedIssuesListView.as_view(), name='liked-issues'),
    path('issues/', IssueRetrieveView.as_view(), name="issue-retrieval"),
    path('issue/<int:issue_id>/', IssueRetrieveView.as_view(), name="issue-detail"),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('comments/', CommentCreateView.as_view(), name='create_comment'),
    path('issues/comments/list/<int:issue_id>/', IssueCommentsListView.as_view(), name='list_comments'),
    path('comments/delete/<int:comment_id>/', CommentDeleteView.as_view(), name='delete_comment'),
    path('comments/like/<int:comment_id>/', CommentLikeView.as_view(), name='like_comment'),
    path('comments/liked/', LikedCommentsListView.as_view(), name='liked_comments'),
]
