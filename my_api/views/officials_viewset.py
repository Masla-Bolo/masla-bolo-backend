from .common import (viewsets, StandardResponseMixin, MyApiOfficial, OfficialSerializer, IsAuthenticated, 
                             IsAdmin, IsUser, IsOfficial, status, action)

class OfficialViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = MyApiOfficial.objects.all()
    serializer_class = OfficialSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        action_permissions = {
            "list": [IsAdmin],
            "retrieve": [IsUser],
            "create": [IsOfficial],
            "update": [IsAuthenticated],
            "partial_update": [IsAuthenticated],
            "destroy": [IsAuthenticated],
            "verify": [IsAdmin],
        }
        permission_classes = action_permissions.get(self.action, [IsAuthenticated])
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(message="Official List", data=paginated_data)
        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(message="Official List", data=serializer.data)

    def create(self, request, *args, **kwargs):
        user = request.user
        official = {
            "user": user.id,
            "district_name": request.data.get("district_name"),
            "city_name": request.data.get("city_name"),
            "country_name": request.data.get("country_name"),
        }
        serializer = self.get_serializer(data=official)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.success_response(
            message="Official Created!",
            data={
                "official": serializer.data,
            },
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, url_name="verify", methods=["patch"])
    def verify(self, request, *args, **kwargs):
        official = self.get_object()
        official.user.verified = True
        official.user.save()
        serializer = self.get_serializer(instance=official)
        return self.success_response(
            message="Official Updated",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )