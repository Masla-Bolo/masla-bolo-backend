# from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class MyApiUser(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=20)

    def __str__(self):
        return self.email
