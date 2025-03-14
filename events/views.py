from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from accounts.models import Interest, User
from .models import Attendance, Event, EventImage

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
                Attendance.objects.create(
                    event=event,
                    user=User.objects.get(id=user_id),
                    status='invited'
                )

        if external_guests:
            for guest_name in external_guests:
                if guest_name.strip():
                    Attendance.objects.create(
                        event=event,
                        external_guest=guest_name.strip(),
                        status='invited'
                    )

        messages.success(request, 'Event created successfully!')
        return redirect('home')  # Adjust to your home URL name

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
    events = Event.objects.filter(is_public=True).order_by('start_time')  # Public events, ordered by start time
    return render(request, 'events/events_view.html', {'events': events})

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'events/event_detail.html', {'event': event})