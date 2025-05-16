from .common import (
    IsAdmin,
    IsAuthenticated,
    IsOfficial,
    IsUser,
    MyApiUser,
    MyApiUserSerializer,
    StandardResponseMixin,
    action,
    status,
    viewsets,
)


class UserViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = MyApiUser.objects.all()
    serializer_class = MyApiUserSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        action_permissions = {
            "list": [IsAdmin],
            "retrieve": [IsUser],
            "create": [IsAuthenticated, IsUser, IsAdmin, IsOfficial],
            "update": [IsAuthenticated],
            "partial_update": [IsAuthenticated, IsUser, IsAdmin, IsOfficial],
            "destroy": [IsAuthenticated],
            "verifyOfficial": [IsAdmin],
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

    @action(url_name="profile", detail=False)
    def profile(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)
        return self.success_response(message="User Profile", data=serializer.data)

    def update(self, request, *args, **kwargs):
        # partial = kwargs.pop('partial', False)
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
            return self.success_response(
                message="Account deleted successfully",
                data=f"Account with email {request.user.email} is deleted",
                status=status.HTTP_204_NO_CONTENT,
            )
        return self.error_response(
            message="You do not have permission to delete this account",
            status=status.HTTP_403_FORBIDDEN,
        )

    @action(detail=False, methods=["patch"], url_path="fcmtoken")
    def fcmtoken(self, request, pk=None):
        user = request.user
        fcmToken = request.data.get("token")

        if not fcmToken:
            return self.error_response(
                message="Token is required", status=status.HTTP_400_BAD_REQUEST
            )

        if user.fcm_tokens is None:
            user.fcm_tokens = []

        if fcmToken not in user.fcm_tokens:
            user.fcm_tokens.append(fcmToken)
            user.save()

        return self.success_response(
            message="FCM Token added successfully",
            data={},
            status_code=status.HTTP_200_OK,
        )
