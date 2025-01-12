from .common import (
    viewsets, status, StandardResponseMixin, IsAuthenticated, DjangoFilterBackend, filters, Issue,
    IssueSerializer, IsAdmin, IsOfficial, IsUser, AllowAny, time, Point, Q, 
    MyApiUser, Issue, Like, Notification, Distance,
    find_official_for_point, send_push_notification, remove_keys_from_dict, action, connection, D)

class IssueViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["issue_status"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "likes_count", "comments_count", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = IssueSerializer.setup_eager_loading(queryset, self.request.user)
        categories = self.request.query_params.get("categories", None)
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
            "list": [AllowAny],
            "retrieve": [IsAuthenticated],
            "create": [IsUser],
            "update": [IsUser, IsAdmin],
            "partial_update": [IsUser],
            "destroy": [IsAdmin, IsUser],
            "complete": [IsAdmin, IsUser],
            "approve": [IsAdmin],
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
                status_code=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Fetched Successfully!!",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, permission_classes=[IsUser])
    def my(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().filter(user=request.user))
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(
                message="Fetched Your Issues Successfully!!", data=paginated_data
            )

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Fetched Your Issues Successfully!!", data=serializer.data
        )

    @action(detail=False, permission_classes=[IsOfficial])
    def my_official_issues(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().filter(user=request.user))
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.success_response(
                message="Fetched Your Issues Successfully!!", data=paginated_data
            )

        serializer = self.get_serializer(queryset, many=True)
        return self.success_response(
            message="Fetched Your Issues Successfully!!", data=serializer.data
        )

    @action(detail=True, methods=["patch"], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        issue = self.get_object()
        try:
            issue.change_status(Issue.APPROVED)
            serializer = self.get_serializer(issue).data
            serializer["contact"] = "info.reportit@gmail.com"
            # we have found the official here
            officialUser = find_official_for_point(issue.location)
            if officialUser:
                send_push_notification(
                    tokens=officialUser.user.fcm_tokens,
                    title=f"A New Issue Has Been Assigned to You from {issue.location}",
                )
                officialUser.assigned_issues.append(issue)
                serializer["contact"] = officialUser.user.email
                officialUser.save()

            serializer.save()
            return self.success_response(
                message="Issue Approved",
                data=serializer,
                status_code=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return self.error_response(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Retrival Successful!",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def complete(self, request, pk=None):
        issue = self.get_object()

        # If user is_created
        if request.user != issue.user or request.user.role != MyApiUser.USER:
            return self.error_response(
                message="Only the issue creator can mark this issue as complete",
                data="User Doesn't Match the Issue Creator",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # if issue is_approved
        if issue.issue_status != Issue.APPROVED:
            return self.error_response(
                message="Issue is not approved, cannot be marked as complete",
                data="Issue Not Approved",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        issue.issue_status = Issue.SOLVED
        issue.save()
        return self.success_response(
            message="Issue marked as complete",
            data=issue,
            status_code=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        # pprint(request.data)
        latitude = float(request.data["latitude"])
        longitude = float(request.data["longitude"])
        issue_location = Point(longitude, latitude, srid=4326)
        # print(issue_location)
        cleaned_data = remove_keys_from_dict(request.data.copy(), ["longitude", "latitude"])
        # entries_to_remove = ('latitude', 'longitude')
        # for key in entries_to_remove:
        #     cleaned_data.pop(key, None)
        # # del cleaned_data["longitude"]
        # # del cleaned_data["latitude"]
        cleaned_data["location"] = issue_location

        serializer = self.get_serializer(data=cleaned_data)
        serializer.is_valid(raise_exception=True)

        # latitude = float(serializer.validated_data["latitude"])
        # longitude = float(serializer.validated_data["longitude"])
        # print(latitude, longitude)

        # issue_location = Point(longitude, latitude, srid=4326)

        distance_threshold = D(m=100)

        existing_issue = (
            Issue.objects.filter(
                location__distance_lte=(issue_location, distance_threshold),
                categories=serializer.validated_data["categories"],
            )
            .annotate(distance=Distance("location", issue_location))
            .first()
        )
        # pprint(existing_issue)

        if existing_issue:
            existing_issue_data = self.get_serializer(existing_issue).data
            # pprint(existing_issue_data)

            return self.error_response(
                message="Same Issue Exists within your Area",
                data=existing_issue_data,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(user=self.request.user, location=issue_location)
        return self.success_response(
            message="New Issue Created",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            return self.success_response(
                message="Issue deleted successfully",
                data={},
                status_code=status.HTTP_204_NO_CONTENT,
            )
        return self.error_response(
            message="You do not have permission to delete this issue",
            data="PermissionError",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        issue = self.get_object()
        user = request.user
        like, created = Like.objects.get_or_create(user=user, issue=issue)
        serializer = self.get_serializer(issue).data
        createdNotification = Notification.objects.create(
            user=user,
            screen="issueDetail",
            screen_id=serializer["id"],
            title="Issue Liked",
            description="Issue Description"
        )
        send_push_notification(createdNotification)  
        
        if created:
            issue.likes_count += 1
            issue.save()
            return self.success_response(
                message="Issue liked",
                data={"likes_count": issue.likes_count},
                status_code=status.HTTP_201_CREATED,
            )

        like.delete()
        issue.likes_count -= 1
        issue.save()
        return self.success_response(
            message="Issue Unliked",
            data={"likes_count": issue.likes_count},
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, permission_classes=[IsAuthenticated])
    def liked_issues(self, request):
        user = request.user

        # Prefetch related fields and optimize the query
        liked_issues = Issue.objects.filter(likes__user=user).prefetch_related(
            "likes", "comments"
        )

        liked_issues = IssueSerializer.setup_eager_loading(liked_issues, user)

        page = self.paginate_queryset(liked_issues)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            print(f"Number of queries: {len(connection.queries)}")
            return self.success_response(
                message="Issues Liked by the User",
                data=paginated_data,
                status_code=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(liked_issues, many=True)
        return self.success_response(
            message="Issues Liked by the User",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )