from .common import (
    AllowAny,
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
    Notification,
    Point,
    Q,
    StandardResponseMixin,
    action,
    connection,
    filters,
    find_official_for_point,
    remove_keys_from_dict,
    send_push_notification,
    status,
    time,
    viewsets,
    Response,
    requests,
    GEOSGeometry,
    OSMPolygonExtractor,
    Polygon,
    MultiPolygon,
    get_emergency_contact,
    # CustomPageNumberPagination,
)
from django.core.cache import cache
from django.conf import settings
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


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
        self.osm_extractor = OSMPolygonExtractor()

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


    def create(self, request, *args, **kwargs):
        # pprint(request.data)
        latitude = float(request.data["latitude"])
        longitude = float(request.data["longitude"])
        issue_location = Point(longitude, latitude, srid=4326)
        # print(issue_location)
        cleaned_data = remove_keys_from_dict(
            request.data.copy(), ["longitude", "latitude"]
        )
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
        like, created = Like.objects.get_or_create(user=user, issue=issue)
        serializer = self.get_serializer(issue).data
        createdNotification = Notification.objects.create(
            user=user,
            screen="issueDetail",
            screen_id=serializer["id"],
            title="Issue Liked",
            description="Issue Description",
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

    @action(detail=False, methods=["get"], url_path="in-area")
    def issues_in_area(self, request):
        """
        Under development for more accurate area filtering.
        Get all issues within a specified area using OpenStreetMap polygon data.

        Query Parameters:
        - area_name (required): Name of the area to search for
        - area_type (optional): Type of area ('city', 'country', 'state', 'county', 'any')
        - include_map (optional): Whether to generate a visualization map (true/false)
        """
        area_name = request.query_params.get("area_name")
        area_type = request.query_params.get("area_type", "any")
        include_map = request.query_params.get("include_map", "false").lower() == "true"

        if not area_name:
            return self.error_response(
                message="Missing area_name parameter", 
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            polygon_data = self.osm_extractor.get_area_polygon(area_name, area_type)
            
            if not polygon_data or not polygon_data.get('polygon'):
                return self.error_response(
                    message=f"No polygon found for area '{area_name}'", 
                    data={},
                    status_code=status.HTTP_404_NOT_FOUND
                )
            # print(polygon_data)
            geos_polygon = self._convert_to_geos_geometry(polygon_data)

            if not geos_polygon:
                return self.error_response(
                    message="Failed to process polygon geometry", 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            return self.error_response(
                message=f"Failed to fetch polygon: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            issues_within = Issue.objects.filter(location__within=geos_polygon)
            total_issues = issues_within.count()

            map_file = None
            if include_map and total_issues > 0:
                try:
                    map_file = self._generate_issues_map(polygon_data, issues_within, area_name)
                except Exception:
                    pass

            page = self.paginate_queryset(issues_within)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data).data
            else:
                serializer = self.get_serializer(issues_within, many=True)
                response_data = serializer.data

            area_info = {
                "name": polygon_data['name'],
                "osm_id": polygon_data['osm_id'],
                "osm_type": polygon_data['type'],
                "bounds": polygon_data['bounds'],
                "polygon_count": len(polygon_data['polygon']),
                "total_issues": total_issues
            }

            if map_file:
                area_info["map_file"] = map_file

            if isinstance(response_data, dict):
                response_data.update({"area_info": area_info})
            else:
                response_data = {"issues": response_data, "area_info": area_info}

            return self.success_response(
                message="Issues in area fetched successfully",
                data=response_data,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.error_response(
                message=f"Failed to filter issues: {str(e)}", 
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def _convert_to_geos_geometry(self, polygon_data):
        """
        Convert OSM polygon data to Django GEOSGeometry object.
        """
        try:
            polygons = polygon_data['polygon']

            if not polygons:
                return None

            geos_polygons = []

            for polygon_coords in polygons:
                if len(polygon_coords) < 3:
                    continue

                if polygon_coords[0] != polygon_coords[-1]:
                    polygon_coords.append(polygon_coords[0])

                polygon = Polygon(polygon_coords)
                geos_polygons.append(polygon)

            if not geos_polygons:
                return None

            return geos_polygons[0] if len(geos_polygons) == 1 else MultiPolygon(geos_polygons)

        except Exception as e:
            print(f"Error converting to GEOSGeometry: {e}")
            return None


    def _generate_issues_map(self, polygon_data, issues_queryset, area_name):
        """
        Generate a Folium map showing the area polygon and issues within it.
        """
        try:
            from django.conf import settings
            import os

            safe_area_name = "".join(c for c in area_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            map_filename = f"{safe_area_name.replace(' ', '_')}_issues_map.html"
            map_path = os.path.join(settings.MEDIA_ROOT, 'maps', map_filename)

            os.makedirs(os.path.dirname(map_path), exist_ok=True)

            folium_map = self.osm_extractor.visualize_on_map(
                polygon_data, 
                map_path,
                popup_info=True,
                fit_bounds=True
            )

            if not folium_map:
                return None

            import folium
            from django.contrib.gis.geos import Point

            issue_count = 0
            for issue in issues_queryset[:100]:
                if hasattr(issue, 'location') and issue.location:
                    if isinstance(issue.location, Point):
                        lat, lon = issue.location.y, issue.location.x
                        popup_content = f"""
                        <b>Issue #{issue.id}</b><br>
                        <b>Title:</b> {getattr(issue, 'title', 'N/A')}<br>
                        <b>Status:</b> {getattr(issue, 'status', 'N/A')}<br>
                        <b>Priority:</b> {getattr(issue, 'priority', 'N/A')}<br>
                        <b>Created:</b> {getattr(issue, 'created_at', 'N/A')}
                        """
                        marker_color = self._get_issue_marker_color(issue)
                        folium.Marker(
                            [lat, lon],
                            popup=folium.Popup(popup_content, max_width=250),
                            icon=folium.Icon(color=marker_color, icon='exclamation-sign'),
                            tooltip=f"Issue #{issue.id}"
                        ).add_to(folium_map)
                        issue_count += 1

            self._add_issues_legend(folium_map, issue_count, len(issues_queryset))
            folium_map.save(map_path)

            return f"maps/{map_filename}"

        except Exception:
            return None


    def _get_issue_marker_color(self, issue):
        """Determine marker color based on issue properties."""
        try:
            if hasattr(issue, 'priority'):
                if issue.priority == 'high':
                    return 'red'
                elif issue.priority == 'medium':
                    return 'orange'
                else:
                    return 'green'
            elif hasattr(issue, 'status'):
                if issue.status == 'open':
                    return 'red'
                elif issue.status == 'in_progress':
                    return 'orange'
                else:
                    return 'green'
            else:
                return 'blue'
        except:
            return 'blue'


    def _add_issues_legend(self, folium_map, displayed_count, total_count):
        """Add a legend to the map showing issue information."""
        try:
            import folium

            legend_html = f"""
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 200px; height: 90px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px">
                <b>Issues Information</b><br>
                <i class="fa fa-exclamation-sign" style="color:red"></i> High Priority<br>
                <i class="fa fa-exclamation-sign" style="color:orange"></i> Medium Priority<br>
                <i class="fa fa-exclamation-sign" style="color:green"></i> Low Priority<br>
                <hr>
                Showing: {displayed_count} of {total_count} issues
            </div>
            """
            folium_map.get_root().html.add_child(folium.Element(legend_html))

        except Exception:
            pass

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
