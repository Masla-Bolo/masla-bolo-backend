import random
import time
from datetime import timedelta
from pprint import pprint
import requests

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import Transform
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from django.contrib.gis.measure import D
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError


from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer
from my_api.mixins import StandardResponseMixin
from my_api.models import Comment, Issue, Like, MyApiOfficial, MyApiUser, Notification, AreaLocation
from my_api.permissions import IsAdmin, IsOfficial, IsUser
from my_api.serializers import (
    CommentSerializer,
    IssueSerializer,
    LoginSerializer,
    MyApiUserSerializer,
    NotificationSerializer,
    OfficialSerializer,
    RegisterSerializer,
    SocialRegisterSerializer,
    VerifyEmailSerializer,
)
from my_api.utils import (
    find_official_for_point,
    remove_keys_from_dict,
    send_push_notification,
    OSMPolygonExtractor,
    get_emergency_contact,
    reverse_geocode,
    fetch_boundary_from_overpass,
    get_emergency_contact_info
)

from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
