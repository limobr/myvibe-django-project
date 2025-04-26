from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from accounts.models import Interest, UserProfile, Notification
from django.utils import timezone
from django.contrib import messages
import json
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from myvibeapp.models import Comment, Media, Post
from django.db.models import Count, Q
from django.urls import reverse

@login_required
def admin_dashboard(request):
    # Check if the logged-in user is an admin
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")
    return render(request, 'admin/dashboard.html')

@login_required
def view_interests(request):
    # Check if the logged-in user is an admin
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")
    
    # Retrieve all interests from the database
    interests = Interest.objects.all()

    return render(request, 'admin/interests.html', {'interests': interests})

@login_required
def add_interest(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")

    if request.method == "POST":
        # Save new interest
        name = request.POST.get('interest_name')
        description = request.POST.get('interest_description')
        interest = Interest.objects.create(name=name, description=description)
        
        # Notify users with related interests
        related_users = UserProfile.objects.filter(interests__in=interest.related_interests.all()).exclude(user=request.user).distinct()
        for profile in related_users:
            Notification.objects.create(
                recipient=profile.user,
                message=f"A new interest '{interest.name}' has been added that you might like",
                link=reverse('view_interests'),
                is_read=False
            )
        
        # Add success message
        messages.success(request, 'Interest was created successfully.')
        
        return redirect('view_interests')

@login_required
def edit_interest(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")

    if request.method == "POST":
        interest_id = request.POST.get('interest_id')
        interest = get_object_or_404(Interest, id=interest_id)
        old_name = interest.name
        interest.name = request.POST.get('interest_name')
        interest.description = request.POST.get('interest_description')
        interest.save()

        # Notify users with this interest or related interests about the update
        if old_name != interest.name:
            related_users = UserProfile.objects.filter(
                Q(interests=interest) | Q(interests__in=interest.related_interests.all())
            ).exclude(user=request.user).distinct()
            for profile in related_users:
                Notification.objects.create(
                    recipient=profile.user,
                    message=f"The interest '{old_name}' has been updated to '{interest.name}'",
                    link=reverse('view_interests'),
                    is_read=False
                )

        # Add success message
        messages.success(request, 'Interest was modified successfully.')
        
        return redirect('view_interests')

@login_required
def delete_interest(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")

    if request.method == "POST":
        interest_id = request.POST.get('interest_id')
        interest = get_object_or_404(Interest, id=interest_id)
        interest_name = interest.name
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

def shorten_location(location):
    # Simplified example: truncate location string if too long
    if len(location) > 20:
        return location[:17] + "..."
    return location

@login_required
def home_view(request):
    # Check if this is the user's first visit to the homepage
    user_profile = request.user.userprofile
    is_first_visit = not user_profile.has_visited_homepage

    # If it's the first visit, mark it as visited
    if is_first_visit:
        user_profile.has_visited_homepage = True
        user_profile.save()

    # Fetch posts
    posts = Post.objects.filter(is_active=True, privacy='public').order_by('-created_at')
    for post in posts:
        if post.location:
            post.short_location = shorten_location(post.location)
        else:
            post.short_location = None

    context = {
        'posts': posts,
        'is_first_visit': is_first_visit  # Pass the flag to the template
    }
    return render(request, 'myvibe/homepage.html', context)

def post_detail_modal(request, post_id):
    post = get_object_or_404(Post, id=post_id, is_active=True)
    return render(request, 'myvibe/post_detail_modal.html', {'post': post})

@csrf_exempt
@login_required
def add_comment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            post_id = data.get('post_id')
            text = data.get('text')

            # Validate input
            if not post_id or not text:
                return JsonResponse({'success': False, 'error': 'Missing post_id or text'}, status=400)

            # Create the comment
            post = Post.objects.get(id=post_id)
            comment = Comment.objects.create(
                user=request.user,
                post=post,
                text=text
            )

            # Notify the post owner (if not the commenter)
            if post.user != request.user:
                Notification.objects.create(
                    recipient=post.user,
                    message=f"{request.user.username} commented on your post",
                    link=reverse('post_detail', kwargs={'post_id': post.id}),
                    is_read=False
                )

            # Return the comment data with created_at in ISO format
            return JsonResponse({
                'success': True,
                'comment': {
                    'text': comment.text,
                    'user': comment.user.get_full_name() or comment.user.username,
                    'created_at': comment.created_at.isoformat()  # ISO 8601 format
                }
            })
        except Post.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Post not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

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

        # Notify followers about the new post (if public)
        if post.privacy == 'public':
            followers = user_profile.followers
            for follower in followers:
                Notification.objects.create(
                    recipient=follower.user,
                    message=f"{request.user.username} created a new post",
                    link=reverse('post_detail', kwargs={'post_id': post.id}),
                    is_read=False
                )

        # Redirect to homepage after post creation
        return redirect('home')

    # Get all interests and serialize to JSON
    all_interests = Interest.objects.all()
    all_interests_json = [
        {'id': interest.id, 'name': interest.name}
        for interest in all_interests
    ]

    # Get user's interests
    user_interests = user_profile.interests.all()
    user_interest_ids = list(user_interests.values_list('id', flat=True))

    return render(request, 'myvibe/create_post.html', {
        'interests': all_interests_json,  # Pass serialized interests
        'user_interest_ids': user_interest_ids,
        'user_interests': user_interests,
    })

@login_required
def discover_users(request):
    user_profile = request.user.userprofile
    user_interests = set(user_profile.interests.all())

    # Group 1: Exact Interest Match
    exact_match_users = UserProfile.objects.exclude(user=request.user).annotate(
        interest_count=Count('interests')
    ).filter(
        interests__in=user_interests,
        interest_count=len(user_interests)
    ).distinct()

    # Exclude exact matches from further groups
    exclude_ids = list(exact_match_users.values_list('id', flat=True))

    # Group 2: Group Members (Placeholder, as no group model exists)
    group_members = UserProfile.objects.none()  # Replace with group logic if available
    exclude_ids.extend(group_members.values_list('id', flat=True))

    # Group 3: Closest Interests (sorted by shared interest count)
    closest_users = UserProfile.objects.exclude(
        user=request.user
    ).exclude(
        id__in=exclude_ids
    ).annotate(
        shared_interests=Count('interests', filter=Q(interests__in=user_interests))
    ).filter(
        shared_interests__gt=0
    ).order_by('-shared_interests')
    exclude_ids.extend(closest_users.values_list('id', flat=True))

    # Group 4: Other Users (all remaining users not in the above groups)
    other_users = UserProfile.objects.exclude(
        user=request.user
    ).exclude(
        id__in=exclude_ids
    ).order_by('-user__date_joined')  # Sort by join date, newest first

    context = {
        'exact_match_users': exact_match_users,
        'group_members': group_members,
        'closest_users': closest_users,
        'other_users': other_users,
        'user_interests': user_interests,
    }
    return render(request, 'myvibe/discover_users.html', context)

@login_required
def follow_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile_id = data.get('profile_id')
            action = data.get('action')  # 'follow' or 'unfollow'
            target_profile = get_object_or_404(UserProfile, id=profile_id)

            if target_profile == request.user.userprofile:
                return JsonResponse({
                    'success': False,
                    'message': 'You cannot follow yourself.'
                }, status=400)

            if action == 'follow':
                request.user.userprofile.follow(target_profile)
                # Notify the target user
                Notification.objects.create(
                    recipient=target_profile.user,
                    message=f"{request.user.username} started following you",
                    link=reverse('discover_users'),  # Adjust URL as needed
                    is_read=False
                )
                messages.success(request, f'You are now following {target_profile.user.username}.')
                return JsonResponse({
                    'success': True,
                    'message': f'You are now following {target_profile.user.username}.',
                    'action': 'unfollow'
                })
            elif action == 'unfollow':
                request.user.userprofile.unfollow(target_profile)
                # Notify the target user
                Notification.objects.create(
                    recipient=target_profile.user,
                    message=f"{request.user.username} unfollowed you",
                    link=reverse('discover_users'),  # Adjust URL as needed
                    is_read=False
                )
                messages.success(request, f'You have unfollowed {target_profile.user.username}.')
                return JsonResponse({
                    'success': True,
                    'message': f'You have unfollowed {target_profile.user.username}.',
                    'action': 'follow'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action.'
                }, status=400)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            }, status=400)
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'User not found.'
            }, status=404)
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    }, status=400)