from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import LoginSerializer, MyApiUserSerializer, RegisterSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.views import APIView
from django.http import Http404
from .models import MyApiUser
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
                return Response({"detail": "Permission denied. You can only access your own data."}, status=status.HTTP_403_FORBIDDEN)

            serializer = MyApiUserSerializer(user)
        else:
            if request.user.role != 'admin':
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
class IssueCreateView(APIView):
    permission_classes = [IsUser]

    def post(self, request, *args, **kwargs):
        # Logic for issue creation should go here
        return Response({"message": "Issue created"}, status=status.HTTP_201_CREATED)

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
