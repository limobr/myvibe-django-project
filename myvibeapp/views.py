from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from accounts.models import Interest
from django.utils import timezone
from django.contrib import messages

from myvibeapp.models import Media, Post

@login_required
def admin_dashboard(request):
    # Check if the logged-in user is an admin.
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")
    return render(request, 'admin/dashboard.html')

@login_required
def view_interests(request):
    # Check if the logged-in user is an admin.
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    # Retrieve all interests from the database
    interests = Interest.objects.all()

    return render(request, 'admin/interests.html', {'interests': interests})


@login_required
def add_interest(request):
    if request.method == "POST":
        # Save new interest
        name = request.POST.get('interest_name')
        description = request.POST.get('interest_description')
        Interest.objects.create(name=name, description=description)
        
        # Add success message
        messages.success(request, 'Interest was created successfully.')
        
        return redirect('view_interests')

@login_required
def edit_interest(request):
    if request.method == "POST":
        interest_id = request.POST.get('interest_id')
        interest = get_object_or_404(Interest, id=interest_id)
        interest.name = request.POST.get('interest_name')
        interest.description = request.POST.get('interest_description')
        interest.save()

        # Add success message
        messages.success(request, 'Interest was modified successfully.')
        
        return redirect('view_interests')

@login_required
def delete_interest(request):
    if request.method == "POST":
        interest_id = request.POST.get('interest_id')
        interest = get_object_or_404(Interest, id=interest_id)
        interest.delete()

        # Add error message for deletion
        messages.error(request, 'Interest was deleted successfully.')
        
        return redirect('view_interests')

# utils.py or inside your view file
def shorten_location(location):
    parts = location.split(',')
    # Return the last two parts (e.g., "Kipkelion East, Kericho County")
    if len(parts) > 2:
        return ', '.join(parts[-3:-1])  # Adjust based on how much detail you want
    return location  # Return the full location if it's already short

@login_required
def home_view(request):
    # Fetch active, public posts ordered by creation date (newest first)
    posts = Post.objects.filter(is_active=True, privacy='public').order_by('-created_at')
    
    # Process each post's location
    for post in posts:
        if post.location:
            post.short_location = shorten_location(post.location)
        else:
            post.short_location = None

    context = {'posts': posts}
    return render(request, 'myvibe/homepage.html', context)


@login_required
def create_post(request):
    user_profile = request.user.userprofile  # Fetch user's profile to get their interests

    if request.method == 'POST':
        description = request.POST.get('description')
        privacy = request.POST.get('privacy')
        location = request.POST.get('location')
        interest_ids = request.POST.getlist('interests')  # Get selected interests
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        # Create the post
        post = Post.objects.create(
            user=request.user,
            description=description,
            privacy=privacy,
            location=location,
            latitude=latitude if latitude else None,
            longitude=longitude if longitude else None
        )

        # Add selected interests to the post
        if interest_ids:
            interests = Interest.objects.filter(id__in=interest_ids)
            post.interests.set(interests)

        # Handle file upload (media)
        if request.FILES.get('media'):
            media_file = request.FILES['media']
            media_type = 'image' if media_file.content_type.startswith('image') else 'video'
            Media.objects.create(post=post, file=media_file, media_type=media_type)

        # Redirect to homepage after post creation
        return redirect('home')

    # Get all interests to display as options and user's interests
    all_interests = Interest.objects.all()
    user_interests = user_profile.interests.all()  # Fetch user's interests

    # Get user interests as a list of IDs for marking defaults in the form
    user_interest_ids = list(user_interests.values_list('id', flat=True))

    return render(request, 'myvibe/create_post.html', {
        'interests': all_interests,
        'user_interest_ids': user_interest_ids,
        'user_interests': user_interests,
    })

