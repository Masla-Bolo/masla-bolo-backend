from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import LoginSerializer, MyApiUserSerializer, RegisterSerializer, IssueSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.views import APIView
from .models import MyApiUser, Issue
from .permissions import IsUser, IsOfficial, IsAdmin

# Retrieve all users or a specific user by ID
class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if user_id:
            try:
                user = MyApiUser.objects.get(pk=user_id)
            except MyApiUser.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            if request.user.role != 'admin' and request.user.id != user.id:
                print(request.user.role)
                return Response({"detail": "Permission denied. You can only access your own data."}, status=status.HTTP_403_FORBIDDEN)

            serializer = MyApiUserSerializer(user)
        else:
            if request.user.role != 'admin':
                # print(request.user.role)
                return Response({"detail": "Permission denied. Only admins can access the list of users."}, status=status.HTTP_403_FORBIDDEN)

            users = MyApiUser.objects.all()
            serializer = MyApiUserSerializer(users, many=True)

        return Response(serializer.data)

    def delete(self, request, user_id):
        if not request.user.role == 'admin':
            return Response({"detail": "Permission denied. Not Admin."}, status=status.HTTP_403_FORBIDDEN)

        try:
            user = MyApiUser.objects.get(pk=user_id)
        except MyApiUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        user.delete()
        return Response({"detail": f"User {user_id} is deleted"}, status=status.HTTP_204_NO_CONTENT)

# Register new users
class RegisterView(generics.CreateAPIView):
    queryset = MyApiUser.objects.all()
    serializer_class = RegisterSerializer

# Login view that returns JWT tokens
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = MyApiUser.objects.get(email=serializer.data['email'])

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)

# Issue creation accessible only by 'user' role
class IssueListCreateView(generics.ListCreateAPIView):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated, IsUser]

    def perform_create(self, serializer):
        # Automatically set the logged-in user as the creator of the issue
        serializer.save(user=self.request.user)

class IssueCompleteView(generics.UpdateAPIView):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        issue = get_object_or_404(Issue, pk=kwargs['pk'])

        # Allow completion only if the request user is the issue creator or an admin
        if request.user == issue.user or request.user.role == MyApiUser.ADMIN:
            issue.issue_status = "completed"
            issue.save()
            return Response({"message": "Issue marked as complete"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "You do not have permission to complete this issue"}, status=status.HTTP_403_FORBIDDEN)

class IssueRetrieveView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, issue_id=None):
        if issue_id:
            issue = get_object_or_404(Issue, pk=issue_id)
            serializer = IssueSerializer(issue)
            return Response(serializer.data)
        else:
            issues = Issue.objects.all()
            serializer = IssueSerializer(issues, many=True)
            return Response(serializer.data)

# Issue approval accessible only by 'admin' role
class IssueApproveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, *args, **kwargs):
        # Logic for issue approval should go here
        return Response({"message": "Issue approved"}, status=status.HTTP_200_OK)

# API view accessible only by 'official' role
class OfficialView(APIView):
    permission_classes = [IsOfficial]

    def get(self, request, *args, **kwargs):
        # Logic for officials should go here
        return Response({"message": "Official view"}, status=status.HTTP_200_OK)
