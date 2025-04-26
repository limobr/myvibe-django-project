from django.db import models  # Standard Django models import
from django.contrib.auth.models import User
from taggit.managers import TaggableManager  # For tags
from myvibeapp.models import Interest  # Assuming your Interest model is in another app

# 1. Event Model
class Event(models.Model):
    EVENT_CATEGORIES = [
        ('workshop', 'Workshop'),
        ('social', 'Social Gathering'),
        ('conference', 'Conference'),
        ('class', 'Class/Training'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    venue_name = models.CharField(max_length=100)  # e.g., "Nairobi School Hall"
    
    # Using latitude and longitude fields instead of PointField
    latitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Latitude of the event location")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Longitude of the event location")
    
    interests = models.ManyToManyField(Interest, related_name='events')
    max_attendees = models.PositiveIntegerField(default=0)  # 0 = unlimited
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    registration_deadline = models.DateTimeField()
    is_public = models.BooleanField(default=True)
    category = models.CharField(max_length=20, choices=EVENT_CATEGORIES)
    tags = TaggableManager()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['category']),
        ]
    def get_primary_image(self):
            """Return the URL of the primary image or a default image if none exists."""
            primary = self.images.filter(is_primary=True).first()
            return primary.image.url if primary else '/static/default_event_image.jpg'
        
    def __str__(self):
        return self.title

# 2. Event Media Model (for event images)
class EventImage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='event_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event.title} - Image {self.pk}"

# 3. Attendance Model
class Attendance(models.Model):
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('attending', 'Attending'),
        ('declined', 'Declined'),
        ('waiting_list', 'Waiting List'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    external_guest = models.CharField(max_length=255, blank=True)  # For non-registered guests
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')
    registration_date = models.DateTimeField(auto_now_add=True)
    check_in_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('event', 'user')  # Prevent duplicate registrations

    def __str__(self):
        return f"{self.user} - {self.status} for {self.event.title}"

# 4. Social Engagement Models
class EventLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return f"{self.user} liked {self.event.title}"

class EventComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)  # For replies

    def __str__(self):
        return f"{self.user} commented on {self.event.title}"

class EventShare(models.Model):
    SHARE_VIA_CHOICES = [
        ('email', 'Email'),
        ('social', 'Social Media'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='shares')
    shared_via = models.CharField(max_length=20, choices=SHARE_VIA_CHOICES)
    shared_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} shared {self.event.title} via {self.shared_via}"

# 5. Event Notification Model
class EventNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('interest_match', 'Interest Match'),
        ('friend_attending', 'Friend Attending'),
        ('reminder', 'Event Reminder'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_notifications')
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user} - {self.notification_type}"


class Invite(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event_invites')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invites')
    sent_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'recipient')