import random
import time
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from .serializers import CommentSerializer, LoginSerializer, MyApiUserSerializer, RegisterSerializer, IssueSerializer, VerifyEmailSerializer, SocialRegisterSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from .models import MyApiUser, Issue, Like, Comment
from rest_framework import filters, status
from django_filters.rest_framework import DjangoFilterBackend
from .permissions import IsUser, IsOfficial, IsAdmin
from django.contrib.auth.models import update_last_login
from django.db.models import Q
from .mixins import StandardResponseMixin
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from django.db import connection

class RegisterView(generics.CreateAPIView, StandardResponseMixin):
    queryset = MyApiUser.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(email_verified=False)

        headers = self.get_success_headers(serializer.data)
        return self.success_response(
            message="Account Registered Successfully!!",
            data={"email": user.email},
            status_code=status.HTTP_200_OK
        )
    
class SocialRegisterView(generics.CreateAPIView, StandardResponseMixin):
    queryset = MyApiUser.objects.all()
    serializer_class = SocialRegisterSerializer

    def create(self, request, *args, **kwargs):
        email = request.data.get("email")
        not_social_user = MyApiUser.objects.filter(
            Q(email=email) & (Q(is_social=False) | Q(is_social=None))
        ).first()
        
        if not_social_user:
            return self.error_response(
                message="User with this email already exists!",
                data={},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        existing_user = MyApiUser.objects.filter(email=email, is_social=True).first()
        if existing_user:
            refresh = RefreshToken.for_user(existing_user)
            return self.success_response(
                message="User already exists, returning existing user.",
                data={
                    'token': str(refresh.access_token),
                    'user': SocialRegisterSerializer(existing_user).data
                },
                status_code=status.HTTP_200_OK
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(email_verified=True)
        
        refresh = RefreshToken.for_user(user)
        return self.success_response(
            message="Account Registered Successfully!",
            data={
                'token': str(refresh.access_token),
                'user': serializer.data
            },
            status_code=status.HTTP_200_OK
        )

class SendEmailView(APIView, StandardResponseMixin):
    def get(self, request, refresh_code=False):
        email = self.request.query_params.get('email')
        user = MyApiUser.objects.get(email=email)

        if user.email_verified:
            self.error_response(message="Email is Already Verified. Try Logging in.", data="AccountExists", status_code=status.HTTP_100_CONTINUE)
        
        # Generate a 6-digit verification code
        verification_code = str(random.randint(100000, 999999))
        
        # Store the code and expiry time in user object (adjust model accordingly)
        user.verification_code = verification_code
        user.code_expiry = timezone.now() + timedelta(minutes=5)  # Code expires in 5 minutes
        user.save()
        
        # Render HTML template
        email_subject = 'Verify your email'
        email_body_html = render_to_string('emails/email_verification_template.html', {
            'username': user.username,
            'verification_code': verification_code
        })
        
        # Send email
        email = EmailMultiAlternatives(
            email_subject,
            email_body_html,
            settings.EMAIL_HOST_USER,
            [user.email]
        )
        email.attach_alternative(email_body_html, "text/html")
        email.send()
        return self.success_response(message="Verification Email Sent Successfully!", data={"email": user.email}, status_code=status.HTTP_200_OK)


class VerifyEmailView(APIView, StandardResponseMixin):
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user = serializer.validated_data["user"]
            update_last_login(None, user)

            refresh = RefreshToken.for_user(user)
            user_data = MyApiUserSerializer(user).data

            return self.success_response(message="Email verified successfully!",data={
                'token': str(refresh.access_token),
                'user': user_data
            }, status_code=status.HTTP_200_OK)
        return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        

class LoginView(generics.GenericAPIView, StandardResponseMixin):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            user_data = MyApiUserSerializer(user).data

            if not user.email_verified:
                return self.success_response(message="Email Not Verified!",data={
                    'user': user_data
                }, status_code=status.HTTP_200_OK)
            
            update_last_login(None, user)
            
            return self.success_response(message="Login Successful!",data={
                'token': str(refresh.access_token),
                'user': user_data
            }, status_code=status.HTTP_200_OK)
        
        return self.error_response(message="Incorrect Credentials", data={"VerificationError"}, status_code=status.HTTP_401_UNAUTHORIZED)

# Issues
class IssueViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['issue_status']
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'likes_count', 'comments_count', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = IssueSerializer.setup_eager_loading(queryset, self.request.user)
        categories = self.request.query_params.get('categories', None)
        if categories:
            categories = categories.split(",")
            category_filter = Q()
            for category in categories:
                category_filter |= Q(categories__contains=[category])
            queryset = queryset.filter(category_filter)

        return queryset


    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        action_permissions = {
            'list': [AllowAny],
            'retrieve': [IsAuthenticated],
            'create': [IsAuthenticated, IsUser],
            'update': [IsAuthenticated, IsUser],
            'partial_update': [IsAuthenticated, IsUser],
            'destroy': [IsAuthenticated, IsUser],
            'complete': [IsAuthenticated, IsUser],
            'approve': [IsAdmin],
        }
        
        permission_classes = action_permissions.get(self.action, [IsAuthenticated])
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        start_time = time.time()
        queryset = self.filter_queryset(self.get_queryset())
        query_time = time.time() - start_time
        print(f"Query time: {query_time}")
        
        page = self.paginate_queryset(queryset)

        if page is not None:
            start_time = time.time()
            serializer = self.get_serializer(page, many=True)
            serialization_time = time.time() - start_time
            print(f"Serialization time: {serialization_time}")
            paginated_data = self.get_paginated_response(serializer.data).data
            print(f"Number of queries: {len(connection.queries)}")
            return self.success_response(
                message="Fetched Successfully!!", 
                data=paginated_data,
                status_code=status.HTTP_200_OK
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Fetched Successfully!!",
            data=serializer.data,  
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, permission_classes=[IsAuthenticated, IsUser])
    def my(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().filter(user=request.user))
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(message="Fetched Your Issues Successfully!!", data=paginated_data)
        
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(message="Fetched Your Issues Successfully!!", data=serializer.data)


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(message="Retrival Successful!", data=serializer.data, status_code=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def complete(self, request, pk=None):
        issue = self.get_object()
        
        # Check if user is the issue creator
        if request.user != issue.user or request.user.role != MyApiUser.USER:
            return self.error_response(
                message="Only the issue creator can mark this issue as complete",
                data="User Doesn't Match the Issue Creator",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if issue is approved
        if issue.issue_status != Issue.APPROVED:
            return self.error_response(
                message="Issue is not approved, cannot be marked as complete",
                data="Issue Not Approved",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        issue.issue_status = Issue.SOLVED
        issue.save()
        return self.success_response(
            message="Issue marked as complete",
            data=issue,
            status_code=status.HTTP_200_OK
        )
        
    @action(detail=True, methods=['patch'])
    def approve(self, request, pk=None):
        issue = self.get_object()
        if issue.issue_status == Issue.APPROVED:
            return self.error_response(
                message="Issue is already approved",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        issue.issue_status = Issue.APPROVED
        issue.save()
        serializer = self.get_serializer(issue)
        return self.success_response(
            message="Issue Approved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
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
            return self.error_response(message="Same Issue Exists from within your Area", data={
                'id': existing_issue.id,
                'detail': 'This Issue Already Exists'
            }, status_code=status.HTTP_400_BAD_REQUEST)

        serializer.save(user=self.request.user)
        return self.success_response(message="New Issue Created", data=serializer.data, status_code=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            return self.success_response(message="Issue deleted successfully", data={}, status_code=status.HTTP_204_NO_CONTENT)
        return self.error_response(message="You do not have permission to delete this issue", data="PermissionError", status_code=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        issue = self.get_object()
        user = request.user
        like, created = Like.objects.get_or_create(user=user, issue=issue)
        # self.send_push_notification(request.user.fcm_tokens, "Issue Like Called", "Body Of the Notification, Ps: You can only send a String")
        
        if created:
            issue.likes_count += 1
            issue.save()
            return self.success_response(message="Issue liked", data={"likes_count": issue.likes_count}, status_code=status.HTTP_201_CREATED)
        
        like.delete()
        issue.likes_count -= 1
        issue.save()
        return self.success_response(message="Issue Unliked", data={"likes_count": issue.likes_count}, status_code=status.HTTP_200_OK)
    
    @action(detail=False, permission_classes=[IsAuthenticated])
    def liked_issues(self, request):
        user = request.user
        
        # Prefetch related fields and optimize the query
        liked_issues = Issue.objects.filter(likes__user=user).prefetch_related('likes', 'comments')
        
        # Optionally use a custom setup_eager_loading method if defined in your serializer
        liked_issues = IssueSerializer.setup_eager_loading(liked_issues, user)

        page = self.paginate_queryset(liked_issues)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            print(f"Number of queries: {len(connection.queries)}")
            return self.success_response(message="Issues Liked by the User", data=paginated_data, status_code=status.HTTP_200_OK)

        serializer = self.get_serializer(liked_issues, many=True)
        return self.success_response(message="Issues Liked by the User", data=serializer.data, status_code=status.HTTP_200_OK)


# Comments
class CommentViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = Comment.objects.filter(parent__isnull=True)
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Apply eager loading
        queryset = CommentSerializer.setup_eager_loading(queryset, self.request)
        # Filter by issue ID if provided
        issue_id = self.request.query_params.get('issueId')
        if issue_id:
            queryset = queryset.filter(issue_id=issue_id)


        # Filter parent comments or comments with replies
        queryset = queryset.filter(
            Q(parent__isnull=True) | Q(replies_count__gt=0)
        )

        # Order by likes_count (descending) and then by created_at (descending)
        queryset = queryset.order_by('-likes_count', '-created_at')

        return queryset

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        action_permissions = {
            'list': [AllowAny],
            'retrieve': [IsAuthenticated],
            'create': [IsAuthenticated],
            'update': [IsAuthenticated],
            'partial_update': [IsAuthenticated],
            'destroy': [IsAuthenticated],
        }
        permission_classes = action_permissions.get(self.action, [IsAuthenticated])
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        issue = get_object_or_404(Issue, id=request.data.get("issueId"))
        parent_id = request.data.get('parentId')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
            if parent_comment.issue != issue:
                return self.error_response(
                    message="Parent comment must belong to the same issue",
                    data="ParentIssueNotSame",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            issue.comments_count += 1
            issue.save()
            serializer.save(issue=parent_comment.issue, parent=parent_comment, user=request.user)
        else:
            issue.comments_count += 1
            issue.save()
            serializer.save(issue=issue, user=request.user)

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f'comments_{issue.id}',
                {
                    'type': 'comment_message',
                    'comment': serializer.data,
                    'user_id': request.user.id
                }
            )

        return self.success_response(
            message="Comment Created Successfully!!",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        
        queryset = self.get_queryset()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            paginated_data = self.get_paginated_response(serializer.data).data
            print(f"Number of queries: {len(connection.queries)}")
            return self.success_response(message="Comment List", data=paginated_data, status_code=status.HTTP_200_OK)

        # If not paginating, serialize the full queryset
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        print(f"Number of queries: {len(connection.queries)}")

        return self.success_response(message="Comment List", data=serializer.data, status_code=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(message="Retrieval Successful!", data=serializer.data, status_code=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        issue = get_object_or_404(Issue, id=request.data.get("issueId"))
        
        # Allow deletion by the comment's author or an admin
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            issue.comments_count -= 1
            issue.save()
            return self.success_response(message="Comment deleted", data={}, status=status.HTTP_204_NO_CONTENT)
        return self.error_response(message="Permission denied", data={}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        comment = self.get_object()
        user = request.user
        like, created = Like.objects.get_or_create(user=user, comment=comment)
        print(f"Number of queries: {len(connection.queries)}")
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
        action_permissions = {
            'list': [IsAdmin],
            'retrieve': [IsUser],
            'create': [IsAuthenticated, IsUser, IsAdmin, IsOfficial],
            'update': [IsAuthenticated],
            'partial_update': [IsAuthenticated, IsUser, IsAdmin, IsOfficial],
            'destroy': [IsAuthenticated],
        }
        permission_classes = action_permissions.get(self.action, [IsAuthenticated])
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
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return self.success_response(message="User Updated", data=serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            return self.success_response(message="Account deleted successfully", data=f"Account with email {request.user.email} is deleted", status=status.HTTP_204_NO_CONTENT)
        return self.error_response(message="You do not have permission to delete this account", status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['patch'], url_path="fcmtoken")
    def fcmtoken(self, request, pk=None):
        user = request.user
        fcmToken = request.data.get("token")

        if not fcmToken:
            return self.error_response(
                message="Token is required",
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.fcm_tokens is None:
            user.fcm_tokens = []

        if fcmToken not in user.fcm_tokens:
            user.fcm_tokens.append(fcmToken)
            user.save()

        return self.success_response(
            message="FCM Token added successfully",
            data={},
            status_code=status.HTTP_200_OK
        )