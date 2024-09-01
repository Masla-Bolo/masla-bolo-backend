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

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if user_id:
            # Retrieve a specific user by ID
            try:
                user = MyApiUser.objects.get(pk=user_id)
            except MyApiUser.DoesNotExist:
                raise Http404
            serializer = MyApiUserSerializer(user)
        else:
            # Retrieve all users
            users = MyApiUser.objects.all()
            serializer = MyApiUserSerializer(users, many=True)
        
        return Response(serializer.data)

    def delete(self, request, user_id):
        # Delete a specific user by ID
        try:
            user = MyApiUser.objects.get(pk=user_id)
        except MyApiUser.DoesNotExist:
            raise Http404
        
        user.delete()
        return Response({"detail": f"User {user_id} is Deleted"},status=status.HTTP_204_NO_CONTENT)

class RegisterView(generics.CreateAPIView):
    queryset = MyApiUser.objects.all()
    serializer_class = RegisterSerializer

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