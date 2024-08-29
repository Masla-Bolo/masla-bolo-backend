from .models import MyApiUser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .serializers import UserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
# from django.contrib.auth import authenticate
from rest_framework.views import APIView

@api_view(['POST'])
def create_user(request):
    # Create a new UserSerializer instance with the data from the request
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
def update_user(request, user_id):
    try:
        user = MyApiUser.objects.get(id=user_id)
    except MyApiUser.DoesNotExist:
        # If the user doesn't exist, return a 404 Not Found status
        return Response(status=status.HTTP_404_NOT_FOUND)
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_user(request, user_id):
    try:
        user = MyApiUser.objects.get(id=user_id)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except MyApiUser.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_users(request):
    users = MyApiUser.objects.all()
    # Serialize the queryset of users, setting many=True for multiple instances
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def register_user(request):
    username = request.data.get('name')
    password = request.data.get('password')
    email = request.data.get('email')

    if username and password:
        user = UserSerializer(data=request.data)
        if user.is_valid():
            user.save()
        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
    return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)




class CustomLoginView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = MyApiUser.objects.get(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


# @api_view(['GET'])
# def get_user_by_id(request, user_id):
#     try:
#         user. User.objects.get(id=user_id)
#     except:
#         return Response(status=status.HTTP_404_NOT_FOUND)