from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Polygon
from django.db import models
from django.utils import timezone
from django.contrib.gis.measure import D

# from jsonschema import ValidationError
from django.core.exceptions import ValidationError


from .utils import get_district_boundary, send_push_notification


class MyApiUserManager(BaseUserManager):
    def create_user(
        self,
        email,
        username,
        location=None,
        role="user",
        password=None,
        verified=False,
        verification_code=None,
        code_expiry=None,
        is_social=False,
    ):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            role=role,
            verified=verified,
            verification_code=verification_code,
            code_expiry=code_expiry,
            is_social=is_social,
            location=location,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_official_user(self, email, username, password, location):
        user = self.create_user(
            email, username, location, password=password, role=MyApiUser.OFFICIAL
        )  # Ensure role is 'official' for superuser
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password, location=None):
        user = self.create_user(
            email, username, location=location, password=password, role=MyApiUser.ADMIN
        )  # Ensure role is 'admin' for superuser
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class MyApiUser(AbstractBaseUser, PermissionsMixin):
    USER = "user"
    OFFICIAL = "official"
    ADMIN = "admin"

    ROLE_CHOICES = [
        (USER, "User"),
        (OFFICIAL, "Official"),
        (ADMIN, "Admin"),
    ]

    email = models.EmailField(unique=True, db_index=True)
    verified = models.BooleanField(default=False)
    is_social = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, null=True, blank=True)
    code_expiry = models.DateTimeField(null=True, blank=True)
    username = models.CharField(max_length=255, unique=True)
    fcm_tokens = models.JSONField(default=list, blank=True)
    profile_image = models.CharField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)
    location = gis_models.PointField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MyApiUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class MyApiOfficial(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="official_profile"
    )
    assigned_issues = models.ManyToManyField(
        "Issue", blank=True, related_name="official_issues"
    )
    area_range = gis_models.PolygonField(default="POLYGON((0 0, 0 0, 0 0, 0 0, 0 0))")
    city_name = models.CharField(max_length=150, null=True, blank=True)
    country_name = models.CharField(max_length=150, null=True, blank=True)
    district_name = models.CharField(max_length=150, null=True, blank=True)
    country_code = models.CharField(max_length=3, editable=False)

    def save(self, *args, **kwargs):
        if self.user.role != MyApiUser.OFFICIAL:
            self.user.role = MyApiUser.OFFICIAL
            self.user.save(update_fields=["role"])
            
        if self.country_name:
            self.country_code = self.country_name[:3].upper()

        if self.city_name and self.country_name:
            coordinates = get_district_boundary(
                self.district_name, self.city_name, self.country_name
            )
            if coordinates:
                self.area_range = Polygon(coordinates)

        super().save(*args, **kwargs)
        if self.area_range:
            issues_in_area = Issue.objects.filter(location__within=self.area_range)
            self.assigned_issues.set(issues_in_area)

    @property
    def total_resolved(self):
        return self.assigned_issues.filter(issue_status=Issue.SOLVED).count()

    def resolved_issues_count(self):
        return self.assigned_issues.filter(issue_status=Issue.SOLVED).count()
    
    def resolved_issues(self):
        return self.assigned_issues.filter(issue_status=Issue.SOLVED)

class AreaLocation(gis_models.Model):
    name = models.CharField(max_length=255)
    city_name = models.CharField(max_length=255)
    country = models.CharField(max_length=255, default="Unknown")
    boundary = gis_models.MultiPolygonField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}, {self.city_name}, {self.country}"

    class Meta:
        unique_together = ('name', 'city_name', 'country')
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['city_name']),
            models.Index(fields=['country']),
            gis_models.Index(fields=['boundary']),
        ]


class Issue(models.Model):
    NOT_APPROVED = "not_approved"
    APPROVED = "approved"
    SOLVING = "solving"
    OFFICIAL_SOLVED = "official_solved"
    SOLVED = "solved"
    REJECTED = "rejected"
    PENDING_USER_CONFIRMATION = "pending_user_confirmation"
    REOPENED = "reopened"

    CATEGORY_CHOICES = [
        ("electric", "Electric"),
        ("gas", "Gas"),
        ("water", "Water"),
        ("waste", "Waste"),
        ("sewerage", "Sewerage"),
        ("stormwater", "Stormwater"),
        ("roads_potholes", "Roads & Potholes"),
        ("road_safety", "Road Safety"),
        ("street_lighting", "Street Lighting"),
        ("public_transportation", "Public Transportation"),
        ("parks_recreation", "Parks & Recreation"),
        ("illegal_dumping", "Illegal Dumping"),
        ("noise_pollution", "Noise Pollution"),
        ("traffic_signals", "Traffic Signals"),
        ("vandalism_graffiti", "Vandalism & Graffiti"),
        ("tree_vegetation_issues", "Tree & Vegetation Issues"),
        ("animal_control", "Animal Control"),
        ("building_safety", "Building Safety"),
        ("fire_safety", "Fire Safety"),
        ("environmental_hazards", "Environmental Hazards"),
        ("parking_violations", "Parking Violations"),
        ("public_health", "Public Health"),
        ("air_quality", "Air Quality"),
        ("zoning_planning", "Zoning & Planning"),
        ("sidewalk_maintenance", "Sidewalk Maintenance"),
        ("public_toilets", "Public Toilets"),
        ("public_safety", "Public Safety"),
        ("other", "Other"),
    ]

    ISSUE_STATUS = [
        (NOT_APPROVED, "Not Approved"),
        (APPROVED, "Approved"),
        (SOLVING, "Solving"),
        (OFFICIAL_SOLVED, "Official Solved"),
        (SOLVED, "Solved"),
        (REJECTED, "Rejected"),
        (PENDING_USER_CONFIRMATION, "Pending User Confirmation"),
        (REOPENED, "Reopened"),
    ]

    ALLOWED_STATUS_CHANGES = {
        NOT_APPROVED: [APPROVED, REJECTED],
        APPROVED: [SOLVING, REJECTED],
        SOLVING: [OFFICIAL_SOLVED, REJECTED],
        OFFICIAL_SOLVED: [PENDING_USER_CONFIRMATION],
        PENDING_USER_CONFIRMATION: [SOLVED, REOPENED],
        REOPENED: [SOLVING, REJECTED],
        REJECTED: [APPROVED],
        SOLVED: [],
    }

    title = models.CharField(max_length=255)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    location = gis_models.PointField(null=True, blank=True)
    description = models.CharField(max_length=280)
    categories = models.JSONField()
    images = models.JSONField()
    issue_status = models.CharField(
        max_length=30,
        choices=ISSUE_STATUS,
        default=NOT_APPROVED,
    )
    is_anonymous = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    area = models.ForeignKey(AreaLocation, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["likes_count"]),
            models.Index(fields=["comments_count"]),
            models.Index(fields=["issue_status"]),
            models.Index(fields=["area"]),
            gis_models.Index(fields=["location"]),
        ]

    def __str__(self):
        return self.title

    def change_status(self, new_status):
        # from .models import MyApiOfficial

        old_status = self.issue_status
        if new_status not in self.ALLOWED_STATUS_CHANGES.get(self.issue_status, []):
            raise ValidationError(
                f"Cannot transition from {self.issue_status} to {new_status}."
            )

        self.issue_status = new_status
        self.save()

        if new_status == self.APPROVED:
            if self.location:
                matching_officials = MyApiOfficial.objects.filter(area_range__covers=self.location)
                for official in matching_officials:
                    official.assigned_issues.add(self)
                nearby_users = MyApiUser.objects.filter(
                    location__distance_lte=(self.location, D(m=500))
                ).exclude(id=self.user.id)

                for user in nearby_users:
                    notification = Notification.objects.create(
                        user=user,
                        screen="issueDetail",
                        screen_id=self.id,
                        title="Nearby Issue Reported",
                        description=f"A new issue titled '{self.title}' has been reported near your area.",
                    )
                    if user.fcm_tokens:
                        send_push_notification(notification)

        if new_status == self.OFFICIAL_SOLVED:
            new_status = self.PENDING_USER_CONFIRMATION
            if new_status in self.ALLOWED_STATUS_CHANGES.get(self.issue_status, []):
                self.issue_status = new_status
                self.save()

        self._notify_user_on_status_change(old_status, new_status)
        self._notify_official_on_status_change(old_status, new_status)


    def _notify_user_on_status_change(self, old_status, new_status):
        status_messages = {
            "not_approved": "Your issue has been submitted and is awaiting admin approval.",
            "approved": "Your issue has been approved and assigned to an official.",
            "solving": "An official is currently working to resolve your issue.",
            "official_solved": "The issue was marked as solved by the official. Please confirm.",
            "solved": "You have confirmed the issue is resolved. Thank you!",
            "rejected": "Your issue was rejected by the admin. Please review or raise again.",
            "pending_user_confirmation": "The official has resolved the issue. Please confirm if it's solved.",
            "reopened": "The issue has been reopened and will be addressed again.",
        }
        
        description = status_messages.get(new_status, f"Issue status changed to '{new_status}'.")

        notification = Notification.objects.create(
            user=self.user,
            screen="issueDetail",
            screen_id=self.id,
            title="Issue Status Updated",
            description=description
        )

        if self.user.fcm_tokens:
            send_push_notification(notification)

    def _notify_official_on_status_change(self, old_status, new_status):
        if new_status not in [self.APPROVED, self.SOLVED]:
            return

        officials = self.official_issues.all()
        if not officials.exists():
            return

        if new_status == self.APPROVED:
            title = "New Issue Assigned"
            description = f"A new issue titled '{self.title}' has been approved and assigned to your area."
        elif new_status == self.SOLVED:
            title = "Issue Marked as Solved"
            description = f"The user has confirmed the issue '{self.title}' is resolved."

        for official in officials:
            user = official.user
            notification = Notification.objects.create(
                user=user,
                screen="issueDetail",
                screen_id=self.id,
                title=title,
                description=description,
            )

            if user.fcm_tokens:
                send_push_notification(notification)

    def clean(self):
        if (
            not self.categories
            or not isinstance(self.categories, list)
            or len(self.categories) < 1
        ):
            raise ValidationError("At least one category must be selected.")

        valid_categories = [choice[1] for choice in self.CATEGORY_CHOICES]
        print(self.categories)
        for category in self.categories:
            if category not in valid_categories:
                # print(category, valid_categories)
                raise ValidationError(f"Invalid category: {category}")

    def save(self, *args, **kwargs):
        self.clean()
        super(Issue, self).save(*args, **kwargs)


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    reply_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reply_to",
    )
    issue = models.ForeignKey(
        "Issue", on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    likes_count = models.PositiveIntegerField(default=0)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ["-likes_count"]  # order comments by likes_count by default
        indexes = [
            models.Index(fields=["issue"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["likes_count"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.issue.title}"


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE, null=True, blank=True, related_name="likes"
    )
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="comments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "issue"]),
            models.Index(fields=["user", "comment"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "issue"], name="unique_issue_like"),
            models.UniqueConstraint(
                fields=["user", "comment"], name="unique_comment_like"
            ),
            models.CheckConstraint(
                check=models.Q(issue__isnull=False) | models.Q(comment__isnull=False),
                name="like_issue_or_comment",
            ),
        ]

    def __str__(self):
        if self.issue:
            return f"Like by {self.user.username} on issue: {self.issue.title}"
        return (
            f"Like by {self.user.username} on comment: {self.comment.content[:20]}..."
        )


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    screen = models.TextField(default="issueDetail")
    screen_id = models.IntegerField(null=True)
    title = models.TextField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# approve ki patch API -> admin issue ka status approve karega...woh bolega yeh issue legit hai...woh db mein dhoondega ke
# iss issue ke lat long ke andar konsa official ata hai...
# woh official jese hi mila...uski id woh nikalega...
# ab issue mein official id ki jagah yeh official ki id ajygi..

# profile page in app -> all issues (pending, not approved, solved) ( for user )
# profile page in app -> all issues (assigned) ( for admin )
# how to get assigned issues? => getIssues?officialId=currentOfficialIdInApp

# approve ki api mein app sendNOtification to only the official, ab agar baad mein
# usko apni list dekhni ho toh woh kia karega? wapis notification mein jayga.
