from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import CommentSerializer, LoginSerializer, MyApiUserSerializer, RegisterSerializer, IssueSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from rest_framework import generics, status, viewsets
from .models import MyApiUser, Issue, Like, Comment
from .permissions import IsUser, IsOfficial, IsAdmin
from django.contrib.auth.models import update_last_login
from django.db.models import Q, Count
from .mixins import StandardResponseMixin

# Auth
class RegisterView(generics.CreateAPIView, StandardResponseMixin):
    queryset = MyApiUser.objects.all()
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return self.success_response(message="Register Successful!", data={
                'user': serializer.data,
                'token': str(refresh.access_token),
            }, status_code=status.HTTP_201_CREATED)
        return self.error_response(message="Registeration Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class LoginView(generics.GenericAPIView, StandardResponseMixin):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        update_last_login(None, user)

        refresh = RefreshToken.for_user(user)
        user_data = MyApiUserSerializer(user).data

        return self.success_response(message="Login Successful!",data={
            'token': str(refresh.access_token),
            'user': user_data
        }, status_code=status.HTTP_200_OK)

# Issues
class IssueViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'list':
            permission_classes = [AllowAny]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsUser]
        elif self.action == 'complete':
            permission_classes = [IsAuthenticated, IsUser]
        elif self.action == 'approve':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data  # Extract the data from the paginated response
            return self.success_response(
                message="Fetched Successfully!!", 
                data=paginated_data,  # Use the extracted data
                status_code=status.HTTP_200_OK
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Fetched Successfully!!",
            data=serializer.data,  # Use the actual data here
            status_code=status.HTTP_200_OK
        )
    
    @action(detail=False, permission_classes=[IsAuthenticated, IsUser])
    def my(self, request, *args, **kwargs):
        user = request.user
        queryset = self.filter_queryset(self.get_queryset().filter(user=user))
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'user': user})
            paginated_data = self.get_paginated_response(serializer.data).data  # Extract the data from the paginated response
            return self.success_response(
                message="Fetched Successfully!!", 
                data=paginated_data,  # Use the extracted data
                status_code=status.HTTP_200_OK
            )
            # return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True, context={'user': user})
        return self.success_response(message="Successful!!", data=serializer.data, status_code=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(message="Retrival Successful!", data=serializer.data, status_code=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        issue = self.get_object()
        issue.issue_status = Issue.SOLVED
        issue.save()
        return self.success_response(message="Issue marked as complete", data=issue, status_code=status.HTTP_200_OK)
        
    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        issue = self.get_object()
        issue.issue_status = Issue.APPROVED
        issue.save()
        return self.success_response(message="Issue approved", data=issue, status_code=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        latitude = serializer.validated_data['latitude']
        longitude = serializer.validated_data['longitude']
        range_delta = 0.001

        existing_issue = Issue.objects.filter(
            Q(latitude__range=(float(latitude) - range_delta, float(latitude) + range_delta)) &
            Q(longitude__range=(float(longitude) - range_delta, float(longitude) + range_delta)) &
            Q(categories=serializer.validated_data['categories'])
        ).first()

        if existing_issue:
            return self.success_response(message="Same Issue Exists from within your Area", data={
                'existing_issue_id': existing_issue.id,
                'detail': 'This Issue Already Exists'
            }, status_code=status.HTTP_200_OK)

        serializer.save(user=self.request.user)
        headers = self.get_success_headers(serializer.data)
        return self.success_response(message="New Issue Created", data=serializer.data, status_code=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            return self.success_response(message="Issue deleted successfully", data={}, status_code=status.HTTP_204_NO_CONTENT)
        return self.error_response(message="You do not have permission to delete this issue", errors="PermissionError", status_code=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        issue = self.get_object()
        user = request.user
        like, created = Like.objects.get_or_create(user=user, issue=issue)
        
        if created:
            issue.likes_count += 1
            issue.save()
            return self.success_response(message="Issue liked", data={"likes_count": issue.likes_count}, status_code=status.HTTP_201_CREATED)
        
        like.delete()
        issue.likes_count -= 1
        issue.save()
        return self.success_response(message="Like removed", data={"likes_count": issue.likes_count}, status_code=status.HTTP_200_OK)
    
    @action(detail=False, permission_classes=[IsAuthenticated])
    def liked_issues(self, request):
        user = request.user
        liked_issues = Issue.objects.filter(likes__user=user)
        page = self.paginate_queryset(liked_issues)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(message="Issues Liked by the User", data=paginated_data, status_code=status.HTTP_200_OK)
        serializer = self.get_serializer(liked_issues, many=True)
        return self.success_response(message="Issues Liked by the User", data=serializer.data, status_code=status.HTTP_200_OK)


# Comments
class CommentViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = Comment.objects.filter(parent__isnull=True)
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'list':
            permission_classes = [AllowAny]
        elif self.action == 'retrieve':
            permission_classes = [IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        issue = get_object_or_404(Issue, id=request.data.get("issueId"))
        parent_id = request.data.get('parentId')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
            serializer.save(issue=parent_comment.issue, parent=parent_comment, user=request.user)
        else:
            serializer.save(issue=issue, user=request.user)

        headers = self.get_success_headers(serializer.data)
        return self.success_response(message="Comment Created Successfully!!", data=serializer.data, status_code=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        issue_id = request.query_params.get('issueId')
        queryset = self.filter_queryset(self.get_queryset())
        if issue_id:
            queryset = queryset.filter(issue_id=issue_id)

        queryset = queryset.annotate(replies_count=Count('replies')).filter(
            Q(parent__isnull=True) | Q(replies_count__gt=0)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(message="Comment List", data=paginated_data, status_code=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(message="Comment List", data=serializer.data, status_code=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(message="Retrieval Successful!", data=serializer.data, status_code=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Allow deletion by the comment's author or an admin
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            return self.success_response(message="Comment deleted", data={}, status=status.HTTP_204_NO_CONTENT)
        return self.error_response(message="Permission denied", data={}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        comment = self.get_object()
        user = request.user
        like, created = Like.objects.get_or_create(user=user, comment=comment)
        
        if created:
            comment.likes_count += 1
            comment.save()
            return self.success_response(message="Comment liked", data={"likes_count": comment.likes_count}, status_code=status.HTTP_201_CREATED)
        
        like.delete()
        comment.likes_count -= 1
        comment.save()
        return self.success_response(message="Comment Unliked", data={"likes_count": comment.likes_count}, status_code=status.HTTP_200_OK)

# Users
class UserViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = MyApiUser.objects.all()
    serializer_class = MyApiUserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'list':
            permission_classes = [IsAdmin]
        elif self.action == 'retrieve':
            permission_classes = [IsUser]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsUser, IsAdmin, IsOfficial]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(message="User List", data=paginated_data)
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(message="User List", data=serializer.data)

    @action(url_name="profile",detail=False)
    def profile(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)
        return self.success_response(message="User Profile", data=serializer.data)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        serializer.is_valid(raise_exception=True)
        instance.save()
        return self.success_response(message="User Updated", data=serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            return self.success_response(message="Account deleted successfully", status=status.HTTP_204_NO_CONTENT)
        return self.error_response(message="You do not have permission to delete this account", status=status.HTTP_403_FORBIDDEN)
