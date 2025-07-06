import hashlib
import json
from .common import (
    AllowAny,
    AreaLocation,
    Count,
    D,
    Distance,
    DjangoFilterBackend,
    IsAdmin,
    IsAuthenticated,
    IsOfficial,
    Issue,
    IssueSerializer,
    IsUser,
    Like,
    MyApiUser,
    MyApiOfficial,
    OfficialSerializer,
    Notification,
    Point,
    Q,
    StandardResponseMixin,
    action,
    connection,
    filters,
    find_official_for_point,
    remove_keys_from_dict,
    reverse_geocode,
    fetch_boundary_from_overpass,
    send_push_notification,
    status,
    time,
    viewsets,
    GEOSGeometry,
    OSMPolygonExtractor,
    Polygon,
    MultiPolygon,
    ValidationError,
    get_emergency_contact,
    # CustomPageNumberPagination,
)
from django.core.cache import cache
from django.conf import settings
# from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


# class IssueRateThrottle(UserRateThrottle):
#     rate = '100/hour'

# class IssueAnonRateThrottle(AnonRateThrottle):
#     rate = '20/hour'


class IssueViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    """
    ViewSet for managing issues in the system.
    
    list:
    Return a list of all issues.
    Query Parameters:
    - issue_status: Filter by issue status
    - categories: Filter by categories (comma-separated)
    - search: Search in title and description
    - ordering: Order by created_at, likes_count, comments_count, or title
    
    create:
    Create a new issue.
    Required fields: title, description, categories, location
    Optional fields: images, is_anonymous
    
    retrieve:
    Get details of a specific issue.
    
    update:
    Update all fields of an existing issue.
    
    partial_update:
    Update specific fields of an existing issue.
    
    destroy:
    Delete an issue.
    """
    
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
    # throttle_classes = [IssueRateThrottle, IssueAnonRateThrottle]
    filterset_fields = ["issue_status"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "likes_count", "comments_count", "title"]
    ordering = ["-created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.osm_extractor = OSMPolygonExtractor()

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
            "complete": [IsUser],
            "approve": [IsAdmin],
        }

        permission_classes = action_permissions.get(self.action, [IsAuthenticated])
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        start_time = time.time()

        # Build a unique cache key using user, query params, and view name
        user_id = request.user.id if request.user.is_authenticated else "anon"
        raw_key = f"issue_list:{user_id}:{json.dumps(request.query_params.dict(), sort_keys=True)}"
        cache_key = "issue_list:" + hashlib.md5(raw_key.encode()).hexdigest()

        cached_response = cache.get(cache_key)
        if cached_response:
            return self.success_response(
                message="Fetched Successfully!! (from cache)",
                data=cached_response,
                status_code=status.HTTP_200_OK,
            )

        # Cache miss → Run the query
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

            cache.set(cache_key, paginated_data, timeout=300)

            return self.success_response(
                message="Fetched Successfully!!",
                data=paginated_data,
                status_code=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=300)
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
        """
        Use the change status api for approval
        """
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

    @action(detail=True, methods=["patch"], permission_classes=[IsUser])
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
        if issue.issue_status == Issue.NOT_APPROVED:
            return self.error_response(
                message="Issue is not approved, cannot be marked as complete",
                data="Issue Not Approved",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        issue.issue_status = Issue.SOLVED
        issue.save()
        serializer = self.get_serializer(issue)
        return self.success_response(
            message="Issue marked as complete",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated], url_path="change-status")
    def change_status(self, request, pk=None):
        issue = self.get_object()
        new_status = request.data.get("new_status")

        if not new_status:
            return self.error_response(
                message="Missing new_status field",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in dict(Issue.ISSUE_STATUS):
            return self.error_response(
                message=f"'{new_status}' is not a valid issue status",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if issue.issue_status == Issue.NOT_APPROVED and new_status not in [Issue.APPROVED, Issue.REJECTED]:
            return self.error_response(
                message="Only approved or rejected transitions are allowed from NOT_APPROVED.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if new_status == Issue.SOLVED:
            if user != issue.user or user.role != MyApiUser.USER:
                return self.error_response(
                    message="Only the issue creator can mark this issue as complete",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        if new_status in [Issue.SOLVING, Issue.OFFICIAL_SOLVED]:
            if user.role not in [MyApiUser.OFFICIAL, MyApiUser.ADMIN]:
                return self.error_response(
                    message="Only officials or Admins can set this status",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        if new_status in [Issue.APPROVED, Issue.REJECTED]:
            if user.role != MyApiUser.ADMIN:
                return self.error_response(
                    message="Only admin can change issue to this status",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        try:
            issue.change_status(new_status)
        except ValidationError as e:
            return self.error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(issue)
        return self.success_response(
            message=f"Issue status updated to '{new_status}'",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )


    def create(self, request, *args, **kwargs):
        user = request.user

        if user.role == MyApiUser.OFFICIAL:
            return self.error_response(
                message="Officials are not allowed to raise issues.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        latitude = float(request.data["latitude"])
        longitude = float(request.data["longitude"])
        issue_location = Point(longitude, latitude, srid=4326)

        cleaned_data = remove_keys_from_dict(request.data.copy(), ["longitude", "latitude"])
        cleaned_data["location"] = issue_location

        serializer = self.get_serializer(data=cleaned_data)
        serializer.is_valid(raise_exception=True)

        # Duplicate prevention
        distance_threshold = D(m=100)
        existing_issue = (
            Issue.objects.filter(
                location__distance_lte=(issue_location, distance_threshold),
                categories=serializer.validated_data["categories"],
            )
            .annotate(distance=Distance("location", issue_location))
            .first()
        )

        if existing_issue:
            existing_issue_data = self.get_serializer(existing_issue).data
            return self.error_response(
                message="Same issue exists within your area.",
                data=existing_issue_data,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Geocode and associate area
        address = reverse_geocode(latitude, longitude)
        town = (
            address.get("suburb")
            or address.get("neighbourhood")
            or address.get("village")
            or address.get("town")
        )
        city = (
            address.get("city")
            or address.get("municipality")
            or address.get("state_district")
            or address.get("county")
        )
        country = address.get("country") or "Unknown"
        town = town or "Unknown"
        city = city or "Unknown"

        area = AreaLocation.objects.filter(name=town, city_name=city, country=country).first()
        if not area:
            print(f"🌐 Fetching boundary for: {town}, {city}, {country}")
            boundary = fetch_boundary_from_overpass(town)
            area = AreaLocation.objects.create(
                name=town,
                city_name=city,
                country=country,
                boundary=boundary
            )

        serializer.save(user=user, location=issue_location, area=area)

        # matching_officials = MyApiOfficial.objects.filter(area_range__contains=issue_location)
        # for official in matching_officials:
        #     official.assigned_issues.add(issue)
        #     official.save()

        return self.success_response(
            message="New issue created",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        print(instance.user, request.user)
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            return self.success_response(
                message="Issue deleted successfully",
                data={},
                status_code=status.HTTP_204_NO_CONTENT,
            )
        return self.error_response(
            message="You do not have permission to delete this issue",
            data={"detali": "PermissionError"},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        issue = self.get_object()
        user = request.user

        if user.role == MyApiUser.OFFICIAL:
            return self.error_response(
                message="Officials are not allowed to like issues.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if issue.issue_status in [Issue.NOT_APPROVED, Issue.REJECTED]:
            return self.error_response(
                message="You cannot like an issue that is not approved or has been rejected.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        like, created = Like.objects.get_or_create(user=user, issue=issue)
        serializer = self.get_serializer(issue).data

        Notification.objects.create(
            user=user,
            screen="issueDetail",
            screen_id=serializer["id"],
            title="Issue Liked",
            description="Issue Description",
        )

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
            message="Issue unliked",
            data={"likes_count": issue.likes_count},
            status_code=status.HTTP_200_OK,
        )
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def nearby(self, request):
        """
        Get issues near a specific location.
        
        Query Parameters:
        - latitude: Latitude of the location (required)
        - longitude: Longitude of the location (required)
        - distance: Search radius in meters (default: 1000)
        
        Returns:
        - List of issues within the specified radius, ordered by distance
        """
        try:
            latitude = float(request.query_params.get("latitude"))
            longitude = float(request.query_params.get("longitude"))
            distance = float(request.query_params.get("distance", 1000))  # in meters
        except (TypeError, ValueError):
            return self.error_response(
                message="Invalid or missing latitude/longitude.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Create a cache key based on location and distance
        cache_key = f"nearby_issues_{latitude}_{longitude}_{distance}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return self.success_response(
                message="Nearby issues fetched successfully (cached)",
                data=cached_data,
                status_code=status.HTTP_200_OK,
            )

        location = Point(longitude, latitude, srid=4326)
        queryset = (
            self.get_queryset()
            .filter(location__distance_lte=(location, D(m=distance)))
            .annotate(distance=Distance("location", location))
            .order_by("distance")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            # Cache for 5 minutes
            cache.set(cache_key, response_data, 300)
            return self.success_response(
                message="Nearby issues fetched successfully",
                data=response_data,
                status_code=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data
        cache.set(cache_key, response_data, 300)
        return self.success_response(
            message="Nearby issues fetched successfully (cached)",
            data=response_data,
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
    @action(detail=False, methods=["get"], url_path="in-area", permission_classes=[IsAuthenticated])
    def issues_in_area(self, request):
        """
        Get all issues that belong to a specified AreaLocation by name (not geometry-based).

        Query Parameters:
        - area_name (optional): Area name to filter issues by
        - city_name (optional): City name to further narrow down the area
        """
        area_name = request.query_params.get("area_name")
        city_name = request.query_params.get("city_name")

        if not area_name and not city_name:
            return self.error_response(
                message="Provide at least area_name or city_name to search",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        area_qs = AreaLocation.objects.all()
        if area_name:
            area_qs = area_qs.filter(name__iexact=area_name)
        if city_name:
            area_qs = area_qs.filter(city_name__iexact=city_name)

        if not area_qs.exists():
            return self.error_response(
                message="No matching AreaLocation found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        issues = Issue.objects.filter(area__in=area_qs).select_related("user")

        page = self.paginate_queryset(issues)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(issues, many=True)
            data = {"issues": serializer.data}

        data["boundaries"] = [
            {
                "area_id": area.id,
                "name": area.name,
                "coords": list(area.boundary.coords) if area.boundary else None
            }
            for area in area_qs if area.boundary
        ]

        return self.success_response(
            message="Issues fetched by area successfully",
            data=data,
            status_code=status.HTTP_200_OK
        )


    @action(detail=False, methods=["get"], permission_classes=[IsOfficial], url_path="official-area-issues")
    def official_area_issues(self, request):
        """
        If the user is official then it will return all the issues related to it.
        """
        user = request.user

        official_profile = user.official_profile.first()
        if not official_profile or not official_profile.area_range:
            return self.error_response(
                message="Official does not have an area_range defined.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        issues = Issue.objects.filter(location__within=official_profile.area_range)

        page = self.paginate_queryset(issues)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(issues, many=True)
            data = {"issues": serializer.data}

        return self.success_response(
            message="Issues within official's area fetched successfully",
            data=data,
            status_code=status.HTTP_200_OK,
        )
        
    @action(detail=False, permission_classes=[IsAuthenticated], url_path='area-counts')
    def area_issue_counts(self, request):
        issues_by_area = (
            Issue.objects
            .filter(area__isnull=False)
            .values(
                "area__id",
                "area__name",
                "area__city_name",
                "area__country"
            )
            .annotate(issue_count=Count("id"))
            .order_by("-issue_count")
        )

        results = [
            {
                "area_id": row["area__id"],
                "name": row["area__name"],
                "city": row["area__city_name"],
                "country": row["area__country"],
                "issue_count": row["issue_count"]
            }
            for row in issues_by_area
        ]

        page = self.paginate_queryset(results)
        if page is not None:
            return self.success_response(
                message="Area-wise Issue Counts",
                data=self.get_paginated_response(page).data,
                status_code=status.HTTP_200_OK,
            )

        return self.success_response(
            message="Area-wise Issue Counts",
            data=results,
            status_code=status.HTTP_200_OK,
        )
    
    @action(detail=True, methods=["get"], url_path="officials", permission_classes=[IsAuthenticated])
    def get_issue_official(self, request, pk=None):
        """
        Returns the officials assigned to a specific issue.
        """
        issue = self.get_object()
        officials = issue.official_issues.select_related("user")

        if not officials.exists():
            return self.error_response(
                message="No officials assigned to this issue.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = OfficialSerializer(officials, many=True, context={"request": request})
        return self.success_response(
            message="Officials fetched successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated], url_path="emergency-contact")
    def get_emergency_contact(self, request, *args, **kwargs):
        issue = self.get_object()
        emergency_contact = get_emergency_contact(issue)
        if emergency_contact:
            return self.success_response(
                message="Emergency contact fetched successfully",
                data=emergency_contact,
                status_code=status.HTTP_200_OK
            )
        else:
            return self.error_response(
                message="No emergency contact found for this issue",
                status_code=status.HTTP_404_NOT_FOUND
            )
