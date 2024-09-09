from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

class MyApiUserManager(BaseUserManager):
    def create_user(self, email, username, role="user", password=None):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), username=username, role=role)  # Use the passed role
        user.set_password(password)  # This hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        user = self.create_user(email, username, password=password, role='admin')  # Ensure role is 'admin' for superuser
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class MyApiUser(AbstractBaseUser, PermissionsMixin):
    USER = 'user'
    OFFICIAL = 'official'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (USER, 'User'),
        (OFFICIAL, 'Official'),
        (ADMIN, 'Admin'),
    ]

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)  # Role field
    created_at = models.DateTimeField(default=timezone.now)  # Automatically set on creation
    updated_at = models.DateTimeField(auto_now=True)  # Automatically update when modified

    objects = MyApiUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

# Issue Model
class Issue(models.Model):
    COMPLETED = "completed"
    APPROVED = "approved"
    NOT_APPROVED = "not_approved"

    CATEGORY_CHOICES = [
        ('electric', 'Electric'),
        ('gas', 'Gas'),
        ('sewerage', 'Sewerage'),
        ('road', 'Road'),
        # Add more categories as needed
    ]
    ISSUE_STATUS = [
        (COMPLETED, 'Completed'),
        (APPROVED, 'Approved'),
        (NOT_APPROVED, 'Not_Approved'),
    ]

    title = models.CharField(max_length=255)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    description = models.CharField(max_length=150)  # Limit to 150 characters
    categories = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    images = models.JSONField()  # Store images as a list of strings (image URLs or paths)
    issue_status = models.CharField(max_length=15, choices=ISSUE_STATUS, default=NOT_APPROVED) # Track completion status
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)  # Automatically set on creation
    updated_at = models.DateTimeField(auto_now=True)  # Automatically update when modified

    def __str__(self):
        return self.title