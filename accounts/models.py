from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import models
from django.templatetags.static import static


class Interest(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    related_interests = models.ManyToManyField('self', blank=True, symmetrical=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        blank=True
    )
    usertype = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='user')
    interests = models.ManyToManyField(Interest, blank=True, related_name='user_profiles')
    email_confirmed = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    last_reset_request = models.DateTimeField(null=True, blank=True)
    theme = models.CharField(max_length=10, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')
    bio = models.CharField(max_length=150, blank=True, null=True, help_text="A short description about yourself (e.g., Tech enthusiast | Photographer | Musician)")
    has_visited_homepage = models.BooleanField(default=False) 
    

    def __str__(self):
        return f"{self.user.username} Profile"

    @property
    def get_profile_picture_url(self):
        """Return the URL of the profile picture or a default image if none exists."""
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return static('assets/myvibe/images/userplaceholder.png')

    @property
    def followers(self):
        """Return queryset of UserProfiles who follow this user."""
        return UserProfile.objects.filter(following__followed=self)

    @property
    def following(self):
        """Return queryset of UserProfiles this user follows."""
        return UserProfile.objects.filter(followed_by__follower=self)

    def follow(self, user_profile):
        """Follow another user profile."""
        if user_profile != self and not Following.objects.filter(follower=self, followed=user_profile).exists():
            Following.objects.create(follower=self, followed=user_profile)

    def unfollow(self, user_profile):
        """Unfollow another user profile."""
        Following.objects.filter(follower=self, followed=user_profile).delete()

    def is_following(self, user_profile):
        """Check if this user follows the given user profile."""
        return Following.objects.filter(follower=self, followed=user_profile).exists()

    def is_followed_by(self, user_profile):
        """Check if this user is followed by the given user profile."""
        return Following.objects.filter(follower=user_profile, followed=self).exists()


class Following(models.Model):
    follower = models.ForeignKey(UserProfile, related_name='following', on_delete=models.CASCADE)
    followed = models.ForeignKey(UserProfile, related_name='followed_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')
        verbose_name = 'Following'
        verbose_name_plural = 'Followings'

    def __str__(self):
        return f"{self.follower.user.username} follows {self.followed.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
    
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255)  # URL to redirect to (e.g., post detail, event page)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message}"

    def get_absolute_url(self):
        return self.link