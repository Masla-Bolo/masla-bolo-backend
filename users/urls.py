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
    path('issues/<int:issue_id>/comments/', CommentCreateView.as_view(), name='create_comment'),
    path('issues/<int:issue_id>/comments/list/', IssueCommentsListView.as_view(), name='list_comments'),
    path('comments/<int:comment_id>/delete/', CommentDeleteView.as_view(), name='delete_comment'),
    path('comments/<int:comment_id>/like/', CommentLikeView.as_view(), name='like_comment'),
    path('comments/liked/', LikedCommentsListView.as_view(), name='liked_comments'),
]
