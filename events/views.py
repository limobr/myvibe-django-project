from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from accounts.models import Interest, User, UserProfile, Notification
from .models import Attendance, Event, EventComment, EventImage, EventLike, EventShare
from django.urls import reverse

@login_required
def create_event(request):
    if request.method == 'POST':
        # Step 1: Basic Details
        title = request.POST.get('title')
        description = request.POST.get('description')
        creator = request.user

        # Step 2: Timing & Venue
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        venue_name = request.POST.get('venue_name')

        # Step 3: Location
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        # Step 4: Interests
        interest_ids = request.POST.getlist('interests')

        # Step 5: Logistics
        max_attendees = request.POST.get('max_attendees', 0)
        price = request.POST.get('price', 0.00)
        registration_deadline = request.POST.get('registration_deadline')
        is_public = request.POST.get('is_public') == 'true'
        category = request.POST.get('category')

        # Create Event
        event = Event.objects.create(
            title=title,
            description=description,
            creator=creator,
            start_time=start_time,
            end_time=end_time,
            venue_name=venue_name,
            latitude=latitude,
            longitude=longitude,
            max_attendees=max_attendees,
            price=price,
            registration_deadline=registration_deadline,
            is_public=is_public,
            category=category
        )

        # Add Interests
        if interest_ids:
            event.interests.set(Interest.objects.filter(id__in=interest_ids))

        # Step 6: Event Images
        images = [request.FILES.get(f'image_{i}') for i in range(1, 4)]
        for i, image in enumerate(images, 1):
            if image:
                EventImage.objects.create(
                    event=event,
                    image=image,
                    is_primary=(i == 1)  # First image is primary
                )

        # Step 7: Invited Guests
        invited_user_ids = request.POST.getlist('invited_users')
        external_guests = request.POST.get('external_guests', '').splitlines()

        if invited_user_ids:
            for user_id in invited_user_ids:
                user = User.objects.get(id=user_id)
                Attendance.objects.create(
                    event=event,
                    user=user,
                    status='invited'
                )
                # Notify invited users
                Notification.objects.create(
                    recipient=user,
                    message=f"You've been invited to the event '{event.title}' by {creator.username}",
                    link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                    is_read=False
                )

        if external_guests:
            for guest_name in external_guests:
                if guest_name.strip():
                    Attendance.objects.create(
                        event=event,
                        external_guest=guest_name.strip(),
                        status='invited'
                    )

        # Notify followers and users with matching interests (if public)
        if is_public:
            # Notify followers
            creator_profile = creator.userprofile
            followers = creator_profile.followers
            for follower in followers:
                Notification.objects.create(
                    recipient=follower.user,
                    message=f"{creator.username} created a new event: '{event.title}'",
                    link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                    is_read=False
                )

            # Notify users with matching interests (excluding creator and already invited users)
            invited_users = User.objects.filter(attendance__event=event, attendance__status='invited')
            event_interests = event.interests.all()
            interested_users = UserProfile.objects.filter(interests__in=event_interests).exclude(
                user=creator
            ).exclude(
                user__in=invited_users
            ).distinct()
            for profile in interested_users:
                Notification.objects.create(
                    recipient=profile.user,
                    message=f"A new event '{event.title}' matches your interests",
                    link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                    is_read=False
                )

        messages.success(request, 'Event created successfully!')
        return redirect('myvibeapp:home')  # Adjusted to match app namespace

    # GET request: Render the form
    interests = Interest.objects.all()
    users = User.objects.exclude(id=request.user.id)  # Exclude the creator
    event_categories = Event.EVENT_CATEGORIES
    context = {
        'interests': interests,
        'users': users,
        'event_categories': event_categories,
    }
    return render(request, 'events/create-event.html', context)

def events_view(request):
    events = Event.objects.filter(is_public=True).order_by('start_time')
    for event in events:
        # Attach the primary image to the event object
        event.primary_image = event.images.filter(is_primary=True).first()
    return render(request, 'events/events_view.html', {'events': events})

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Attendance status for the current user
    attendance = None
    if request.user.is_authenticated:
        attendance = Attendance.objects.filter(event=event, user=request.user).first()
    
    # Likes information
    likes_count = event.likes.count()
    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = event.likes.filter(user=request.user).exists()
    
    # Comments
    comments = event.comments.all()
    
    context = {
        'event': event,
        'attendance': attendance,
        'likes_count': likes_count,
        'user_has_liked': user_has_liked,
        'comments': comments,
    }
    return render(request, 'events/event_detail.html', context)

@login_required
def like_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    like, created = EventLike.objects.get_or_create(user=request.user, event=event)
    if created:
        # Notify the event creator (if not the liker)
        if event.creator != request.user:
            Notification.objects.create(
                recipient=event.creator,
                message=f"{request.user.username} liked your event '{event.title}'",
                link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                is_read=False
            )
    else:
        like.delete()  # Unlike if already liked
    return redirect('events:event_detail', event_id=event_id)

@login_required
def share_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        shared_via = request.POST.get('shared_via', 'social')  # Default to social media
        EventShare.objects.create(user=request.user, event=event, shared_via=shared_via)
        
        # Notify the event creator (if not the sharer)
        if event.creator != request.user:
            Notification.objects.create(
                recipient=event.creator,
                message=f"{request.user.username} shared your event '{event.title}'",
                link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                is_read=False
            )
        
        messages.success(request, 'Event shared successfully!')
    return redirect('events:event_detail', event_id=event_id)

@login_required
def add_comment(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            comment = EventComment.objects.create(user=request.user, event=event, content=content)
            
            # Notify the event creator (if not the commenter)
            if event.creator != request.user:
                Notification.objects.create(
                    recipient=event.creator,
                    message=f"{request.user.username} commented on your event '{event.title}'",
                    link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                    is_read=False
                )
            
            messages.success(request, 'Comment added!')
    return redirect('events:event_detail', event_id=event_id)

@login_required
def join_waiting_list(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not Attendance.objects.filter(event=event, user=request.user).exists():
        # Check if max attendees is reached (if not unlimited)
        if event.max_attendees > 0 and event.attendees.filter(status='attending').count() >= event.max_attendees:
            attendance = Attendance.objects.create(event=event, user=request.user, status='waiting_list')
            messages.success(request, 'You have joined the waiting list.')
            
            # Notify the event creator
            Notification.objects.create(
                recipient=event.creator,
                message=f"{request.user.username} joined the waiting list for your event '{event.title}'",
                link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                is_read=False
            )
        else:
            attendance = Attendance.objects.create(event=event, user=request.user, status='attending')
            messages.success(request, 'You are now attending the event.')
            
            # Notify the event creator
            Notification.objects.create(
                recipient=event.creator,
                message=f"{request.user.username} is attending your event '{event.title}'",
                link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                is_read=False
            )
    else:
        messages.error(request, 'You are already registered for this event.')
    return redirect('events:event_detail', event_id=event_id)

@login_required
def accept_invite(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    attendance = Attendance.objects.filter(event=event, user=request.user, status='invited').first()
    if attendance:
        # Check if max attendees allows acceptance
        if event.max_attendees > 0 and event.attendees.filter(status='attending').count() >= event.max_attendees:
            attendance.status = 'waiting_list'
            messages.info(request, 'Event is full. You have been placed on the waiting list.')
            
            # Notify the event creator
            Notification.objects.create(
                recipient=event.creator,
                message=f"{request.user.username} accepted your invite but was placed on the waiting list for '{event.title}'",
                link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                is_read=False
            )
        else:
            attendance.status = 'attending'
            messages.success(request, 'You have accepted the invite and are now attending.')
            
            # Notify the event creator
            Notification.objects.create(
                recipient=event.creator,
                message=f"{request.user.username} accepted your invite and is attending '{event.title}'",
                link=reverse('events:event_detail', kwargs={'event_id': event.id}),
                is_read=False
            )
        attendance.save()
    else:
        messages.error(request, 'You are not invited to this event.')
    return redirect('events:event_detail', event_id=event_id)

