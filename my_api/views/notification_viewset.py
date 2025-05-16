from .common import (
    IsAuthenticated,
    Notification,
    NotificationSerializer,
    StandardResponseMixin,
    action,
    status,
    viewsets,
)


class NotificationViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        action_permissions = {
            "list": [IsAuthenticated],
            "my": [IsAuthenticated],
        }

        permission_classes = action_permissions.get(self.action, [IsAuthenticated])
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(
                message="Fetched Successfully!!",
                data=paginated_data,
                status_code=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Fetched Successfully!!",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, permission_classes=[IsAuthenticated])
    def my(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().filter(user=request.user))
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(
                message="Fetched Your Notifications Successfully!!", data=paginated_data
            )

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Fetched Your Notifications Successfully!!", data=serializer.data
        )
