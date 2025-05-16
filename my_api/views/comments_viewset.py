from .common import (
    AllowAny,
    Comment,
    CommentSerializer,
    IsAuthenticated,
    Issue,
    Like,
    MyApiUser,
    Q,
    StandardResponseMixin,
    action,
    async_to_sync,
    connection,
    get_channel_layer,
    get_object_or_404,
    status,
    viewsets,
)


class CommentViewSet(viewsets.ModelViewSet, StandardResponseMixin):
    queryset = Comment.objects.filter(parent__isnull=True)
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = CommentSerializer.setup_eager_loading(queryset, self.request)
        issue_id = self.request.query_params.get("issueId")
        if issue_id:
            queryset = queryset.filter(issue_id=issue_id)
        queryset = queryset.filter(Q(parent__isnull=True) | Q(replies_count__gt=0))

        queryset = queryset.order_by("-likes_count", "-created_at")

        return queryset

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        action_permissions = {
            "list": [AllowAny],
            "retrieve": [IsAuthenticated],
            "create": [IsAuthenticated],
            "update": [IsAuthenticated],
            "partial_update": [IsAuthenticated],
            "destroy": [IsAuthenticated],
        }
        permission_classes = action_permissions.get(self.action, [IsAuthenticated])
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        issue = get_object_or_404(Issue, id=request.data.get("issueId"))
        parent_id = request.data.get("parentId")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if parent_id:
            parent_comment = get_object_or_404(Comment, id=parent_id)
            if parent_comment.issue != issue:
                return self.error_response(
                    message="Parent comment must belong to the same issue",
                    data="ParentIssueNotSame",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            issue.comments_count += 1
            issue.save()
            serializer.save(
                issue=parent_comment.issue, parent=parent_comment, user=request.user
            )
        else:
            issue.comments_count += 1
            issue.save()
            serializer.save(issue=issue, user=request.user)

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"comments_{issue.id}",
                {
                    "type": "comment_message",
                    "comment": serializer.data,
                    "user_id": request.user.id,
                },
            )

        return self.success_response(
            message="Comment Created Successfully!!",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):

        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={"request": request}
            )
            paginated_data = self.get_paginated_response(serializer.data).data
            print(f"Number of queries: {len(connection.queries)}")
            return self.success_response(
                message="Comment List",
                data=paginated_data,
                status_code=status.HTTP_200_OK,
            )

        # If not paginating, serialize the full queryset
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        print(f"Number of queries: {len(connection.queries)}")

        return self.success_response(
            message="Comment List", data=serializer.data, status_code=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(
            message="Retrieval Successful!",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        issue = get_object_or_404(Issue, id=request.data.get("issueId"))

        # Allow deletion by the comment's author or an admin
        if request.user == instance.user or request.user.role == MyApiUser.ADMIN:
            self.perform_destroy(instance)
            issue.comments_count -= 1
            issue.save()
            return self.success_response(
                message="Comment deleted", data={}, status=status.HTTP_204_NO_CONTENT
            )
        return self.error_response(
            message="Permission denied", data={}, status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        comment = self.get_object()
        user = request.user
        like, created = Like.objects.get_or_create(user=user, comment=comment)
        print(f"Number of queries: {len(connection.queries)}")
        if created:
            comment.likes_count += 1
            comment.save()
            return self.success_response(
                message="Comment liked",
                data={"likes_count": comment.likes_count},
                status_code=status.HTTP_201_CREATED,
            )

        like.delete()
        comment.likes_count -= 1
        comment.save()
        return self.success_response(
            message="Comment Unliked",
            data={"likes_count": comment.likes_count},
            status_code=status.HTTP_200_OK,
        )
