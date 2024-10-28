from django.urls import re_path
from . import consumer

websocket_urlpatterns = [
    re_path(r'ws/comments/(?P<issue_id>\w+)/$', consumer.CommentConsumer.as_asgi()),
]