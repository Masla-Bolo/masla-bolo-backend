from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from jsonschema import ValidationError

class MyApiUserManager(BaseUserManager):
    def create_user(self, email, username, role="user", password=None, email_verified=False, verification_code=None, code_expiry=None, is_social=False):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), username=username, role=role, email_verified=email_verified, verification_code=verification_code, code_expiry=code_expiry, is_social=is_social)  # Use the passed role
        user.set_password(password)  # This hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        user = self.create_user(email, username, password=password, role=MyApiUser.ADMIN)  # Ensure role is 'admin' for superuser
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
    email_verified = models.BooleanField(default=False)
    is_social = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    code_expiry = models.DateTimeField(null=True, blank=True)
    username = models.CharField(max_length=255, unique=True)
    fcm_tokens = models.JSONField(default=list, blank=True)
    profile_image = models.CharField(max_length=500, null=True, blank=True)
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
    SOLVED = "solved"
    APPROVED = "approved"
    NOT_APPROVED = "not_approved"

    CATEGORY_CHOICES = [
        ('electric', 'Electric'),
        ('gas', 'Gas'),
        ('water', 'Water'),
        ('waste', 'Waste'),
        ('sewerage', 'Sewerage'),
        ('stormwater', 'Stormwater'),
        ('roads_potholes', 'Roads & Potholes'),
        ('road_safety', 'Road Safety'),
        ('street_lighting', 'Street Lighting'),
        ('public_transportation', 'Public Transportation'),
        ('parks_recreation', 'Parks & Recreation'),
        ('illegal_dumping', 'Illegal Dumping'),
        ('noise_pollution', 'Noise Pollution'),
        ('traffic_signals', 'Traffic Signals'),
        ('vandalism_graffiti', 'Vandalism & Graffiti'),
        ('tree_vegetation_issues', 'Tree & Vegetation Issues'),
        ('animal_control', 'Animal Control'),
        ('building_safety', 'Building Safety'),
        ('fire_safety', 'Fire Safety'),
        ('environmental_hazards', 'Environmental Hazards'),
        ('parking_violations', 'Parking Violations'),
        ('public_health', 'Public Health'),
        ('air_quality', 'Air Quality'),
        ('zoning_planning', 'Zoning & Planning'),
        ('sidewalk_maintenance', 'Sidewalk Maintenance'),
        ('public_toilets', 'Public Toilets'),
        ('public_safety', 'Public Safety'),
        ('other', 'Other'),
    ]
    
    ISSUE_STATUS = [
        (SOLVED, 'Solved'),
        (APPROVED, 'Approved'),
        (NOT_APPROVED, 'Not_Approved'),
    ]

    title = models.CharField(max_length=255)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=12, decimal_places=10)
    longitude = models.DecimalField(max_digits=12, decimal_places=10)
    description = models.CharField(max_length=280)  # Limit to 150 characters
    categories = models.JSONField()
    images = models.JSONField()  # Store images as a list of strings (image URLs or paths)
    issue_status = models.CharField(max_length=15, choices=ISSUE_STATUS, default=NOT_APPROVED) # Track completion status
    is_anonymous = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)  # Automatically set on creation
    updated_at = models.DateTimeField(auto_now=True)  # Automatically update when modified

    class Meta:
        ordering = ['-created_at'] # order comments by recent by default

    def __str__(self):
        return self.title
    
    def clean(self):
        if not self.categories or not isinstance(self.categories, list) or len(self.categories) < 1:
            raise ValidationError("At least one category must be selected.")

        valid_categories = [choice[1] for choice in self.CATEGORY_CHOICES]
        for category in self.categories:
            if category not in valid_categories:
                raise ValidationError(f"Invalid category: {category}")

    def save(self, *args, **kwargs):
        self.clean()
        super(Issue, self).save(*args, **kwargs)
    

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    reply_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='reply_to')
    issue = models.ForeignKey('Issue', on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    likes_count = models.PositiveIntegerField(default=0)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['-likes_count'] # order comments by likes_count by default

    def __str__(self):
        return f'Comment by {self.user.username} on {self.issue.title}'

class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'issue'], name='unique_issue_like'),
            models.UniqueConstraint(fields=['user', 'comment'], name='unique_comment_like'),
            models.CheckConstraint(
                check=models.Q(issue__isnull=False) | models.Q(comment__isnull=False),
                name='like_issue_or_comment'
            )
        ]

    def __str__(self):
        if self.issue:
            return f'Like by {self.user.username} on issue: {self.issue.title}'
        return f'Like by {self.user.username} on comment: {self.comment.content[:20]}...'