from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class MyApiUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, role="user"):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), username=username, role=role)  # Use the passed role
        user.set_password(password)  # This hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        user = self.create_user(email, username, password, role='admin')  # Ensure role is 'admin' for superuser
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

    objects = MyApiUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
