from django.db import models
from django.contrib.auth.models import User
from accounts.models import Interest  # Assuming Interest is in the accounts app

class Post(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('friends', 'Friends Only'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    description = models.TextField()
    interests = models.ManyToManyField(Interest, related_name='posts', blank=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='public')
    location = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(blank=True, null=True)  # For geotagging
    longitude = models.FloatField(blank=True, null=True)  # For geotagging
    is_active = models.BooleanField(default=True)  # For soft deletion

    # Denormalized counters for performance
    total_likes = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    total_shares = models.PositiveIntegerField(default=0)
    total_views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['privacy']),
        ]

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"


class Media(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='posts/media/')
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPE_CHOICES)
    order = models.PositiveSmallIntegerField(default=0)  # For sorting media
    thumbnail = models.ImageField(upload_to='posts/thumbnails/', blank=True)  # For video previews
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)  # For nested comments
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['created_at']

class Share(models.Model):
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_posts')
    shared_at = models.DateTimeField(auto_now_add=True)
    caption = models.TextField(blank=True)  # Optional comment when sharing

    class Meta:
        ordering = ['-shared_at']

class View(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Allow anonymous views
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()  # For analytics

    class Meta:
        ordering = ['-viewed_at']


