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
from django.contrib.auth.models import update_last_login

# List all users (Admin only)
class UserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        users = MyApiUser.objects.all()
        serializer = MyApiUserSerializer(users, many=True)
        return Response(serializer.data)


# Retrieve a specific user (Admins or the user themselves)
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            # Check if the user is trying to access their own details
            if request.user.id != user_id and request.user.role != MyApiUser.ADMIN:
                # If not, fetch the details of the currently logged-in user
                user = MyApiUser.objects.get(pk=request.user.id)
            else:
                # Fetch the details of the requested user (user_id)
                user = MyApiUser.objects.get(pk=user_id)
        except MyApiUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the user data and return it in the response
        serializer = MyApiUserSerializer(user)
        return Response(serializer.data)


# Delete a specific user (Admin or User itself)
class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        try:
            user = MyApiUser.objects.get(pk=user_id)
        except MyApiUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Allow deletion if the request is made by an admin or the user themselves
        if request.user.role == MyApiUser.ADMIN or request.user.id == user.id:
            user.delete()
            return Response({"detail": f"User {user_id} is deleted"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "Permission denied. You can only delete your own account."}, status=status.HTTP_403_FORBIDDEN)

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
        user = serializer.validated_data['user']  # Extract the user instance

        update_last_login(None, user)

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
            issue.issue_status = Issue.COMPLETED
            issue.save()
            return Response({"message": "Issue marked as complete"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "You do not have permission to complete this issue"}, status=status.HTTP_403_FORBIDDEN)

class IssueRetrieveView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, issue_id=None):
        if issue_id:
            try:
                issue = Issue.objects.get(pk=issue_id)
            except Issue.DoesNotExist:
                return Response({"error": "Issue Not Found"}, status=status.HTTP_404_NOT_FOUND)

            serializer = IssueSerializer(issue)
            return Response(serializer.data)
        else:
            issues = Issue.objects.all()
            serializer = IssueSerializer(issues, many=True)
            return Response(serializer.data)


        
class IssueDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, issue_id):
        try:
            issue = Issue.objects.get(pk=issue_id)
        except Issue.DoesNotExist:
            return Response({"error": "Issue Not Found"}, status=status.HTTP_404_NOT_FOUND)

        # Allow deletion only if the request user is the issue creator or an admin
        if request.user == issue.user or request.user.role == MyApiUser.ADMIN:
            issue.delete()
            return Response({"message": "Issue deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "You do not have permission to delete this issue"}, status=status.HTTP_403_FORBIDDEN)

# Issue approval accessible only by 'admin' role
class IssueApproveView(APIView):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAdmin]

    def patch(self, request, *args, **kwargs):
        issue = get_object_or_404(Issue, pk=kwargs['pk'])

        # Allow completion only if the request user is the issue creator or an admin
        if request.user == issue.user or request.user.role == MyApiUser.ADMIN:
            issue.issue_status = Issue.APPROVED
            issue.save()
            return Response({"message": "Issue is Approved"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "You do not have permission to complete this issue"}, status=status.HTTP_403_FORBIDDEN)

# API view accessible only by 'official' role
class OfficialView(APIView):
    permission_classes = [IsOfficial]

    def get(self, request, *args, **kwargs):
        # Logic for officials should go here
        return Response({"message": "Official view"}, status=status.HTTP_200_OK)
