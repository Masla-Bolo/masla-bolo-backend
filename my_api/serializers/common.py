from django.contrib.auth import authenticate
from django.contrib.gis.geos import Point
from django.db.models import Count, Exists, OuterRef, Prefetch
from django.utils import timezone

from my_api.models import Comment, Issue, Like, MyApiOfficial, MyApiUser, Notification

from rest_framework import serializers
