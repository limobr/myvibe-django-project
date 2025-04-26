from datetime import time
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Following, Interest, Notification, UserProfile
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import logging
import json
from myvibeapp.models import Post, Media
from events.models import Attendance, Event, EventImage, Invite
from django.utils.dateparse import parse_datetime
from decimal import Decimal
from taggit.models import Tag
from django.core.exceptions import PermissionDenied, ValidationError
import pytz
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.staticfiles import finders

logger = logging.getLogger(__name__)

def register(request):
    """Show the registration form and handle user registration"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validation checks
        if not all([first_name, last_name, username, email, password, confirm_password]):
            messages.error(request, 'All fields are required.')
        elif len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already in use.')
        else:
            # Create the user if validation passes
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                user.save()

                # Use get_or_create to avoid duplicate UserProfile entries
                user_profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'usertype': 'user'}
                )
                if not created:
                    user_profile.usertype = 'user'
                    user_profile.save()

                # Log the user in
                auth_login(request, user)

                messages.success(request, "Account created successfully! Please verify your email.")
                return redirect('confirm_email')  # Redirect to confirm email page
            except Exception as e:
                messages.error(request, f"Error creating account: {str(e)}")

        # If validation fails, re-render the form with the submitted data
        return render(request, 'accounts/register.html', {
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'email': email,
        })

    # GET request: render the empty form
    return render(request, 'accounts/register.html')


def login_view(request):
    """Handle user login and redirect based on user type and interests"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'

        # Validation checks
        if not username or not password:
            messages.error(request, "Both username and password are required.")
            return render(request, 'accounts/login.html', {'username': username})

        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            # Handle "Remember me" by setting session expiry
            if not remember_me:
                request.session.set_expiry(0)  # Session expires when browser closes
            else:
                request.session.set_expiry(1209600)  # 2 weeks (default Django session expiry)

            if hasattr(user, 'userprofile'):
                if user.userprofile.usertype == 'admin':
                    return redirect('admin_dashboard')
                else:
                    # Check if the user has interests selected
                    if not user.userprofile.interests.exists():
                        return redirect('select_interests')
                    return redirect('home')
            else:
                messages.error(request, "User profile not found.")
        else:
            messages.error(request, "Invalid username or password.")
        
        # On failed login, re-render the form with the submitted username
        return render(request, 'accounts/login.html', {'username': username})

    # GET request: render the login form
    return render(request, 'accounts/login.html')

# Password reset token generator
token_generator = PasswordResetTokenGenerator()

def forgot_password(request):
    """Handle password reset requests by sending a reset link via email"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        # Validation checks
        if not email:
            messages.error(request, "Email is required.")
            return render(request, 'accounts/forgot_password.html', {'email': email})

        # Check if a user with this email exists
        try:
            user = User.objects.get(email=email)

            # Check for cooldown (1-minute wait between requests)
            if user.userprofile.last_reset_request and timezone.now() - user.userprofile.last_reset_request < timedelta(minutes=1):
                messages.info(request, "Please wait 1 minute before requesting a new reset link.")
                return render(request, 'accounts/forgot_password.html', {'email': email})

            # Generate reset token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)

            # Update last reset request timestamp
            user.userprofile.last_reset_request = timezone.now()
            user.userprofile.save()

            # Prepare email content
            reset_link = request.build_absolute_uri(f"/accounts/reset-password/{uid}/{token}/")
            subject = "Reset Your myVibe Password"
            from_email = "support@myvibe.com"
            to_email = user.email

            html_content = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'reset_link': reset_link,
            })

            # Create and send EmailMessage
            email = EmailMessage(
                subject,
                html_content,
                from_email,
                [to_email],
            )
            email.content_subtype = "html"
            email.send(fail_silently=False)

            messages.success(request, "A password reset link has been sent to your email.")
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, "No account found with this email address.")
            return render(request, 'accounts/forgot_password.html', {'email': email})

    # GET request: render the forgot password form
    return render(request, 'accounts/forgot_password.html')

def reset_password(request, uidb64, token):
    """Handle password reset after user clicks the reset link"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')

            # Validation checks
            if not password or not confirm_password:
                messages.error(request, "Both password fields are required.")
            elif len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
            elif password != confirm_password:
                messages.error(request, "Passwords do not match.")
            else:
                # Update the user's password
                user.set_password(password)
                user.save()
                messages.success(request, "Your password has been reset successfully! Please log in.")
                return redirect('login')

        return render(request, 'accounts/reset_password.html', {'user': user, 'validlink': True})
    else:
        messages.error(request, "The password reset link is invalid or has expired.")
        return render(request, 'accounts/reset_password.html', {'validlink': False})


@login_required
def notifications(request):
    # Get all notifications for the user
    user_notifications = Notification.objects.filter(recipient=request.user)
    
    # Mark unread notifications as read when the page is viewed
    unread_notifications = user_notifications.filter(is_read=False)
    if unread_notifications.exists():
        unread_notifications.update(is_read=True)
    
    return render(request, 'accounts/notifications.html', {
        'notifications': user_notifications
    })

def generate_otp():
    return str(random.randint(100000, 999999))

@login_required
def confirm_email(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    profile = request.user.userprofile
    
    if request.method == 'POST':
        if 'request_otp' in request.POST:
            # Check if a new OTP can be requested (1-minute cooldown)
            if not profile.otp_created_at or timezone.now() - profile.otp_created_at > timedelta(minutes=1):
                otp = generate_otp()
                profile.otp_code = otp
                profile.otp_created_at = timezone.now()
                profile.save()
                
                # Prepare email content
                subject = "Verify Your Email Address for myVibe"
                from_email = "verification@myvibe.com"
                to_email = request.user.email
                
                # Render HTML email template
                html_content = render_to_string('accounts/otp_email.html', {
                    'otp': otp,
                    'user': request.user,
                })
                
                # Create and send EmailMessage
                email = EmailMessage(
                    subject,
                    html_content,
                    from_email,
                    [to_email],
                )
                email.content_subtype = "html"
                email.send(fail_silently=False)
                
                messages.info(request, "OTP has been sent to your email.")
            else:
                messages.info(request, "Please wait 1 minute before requesting a new OTP.")
        elif 'verify_otp' in request.POST:
            entered_otp = request.POST.get('otp')
            if profile.otp_code and profile.otp_created_at:
                if timezone.now() - profile.otp_created_at < timedelta(minutes=2):
                    if entered_otp == profile.otp_code:
                        profile.email_confirmed = True
                        profile.otp_code = None
                        profile.otp_created_at = None
                        profile.save()
                        messages.success(request, "Your email has been confirmed! Please log in to continue.")
                        # Log out the user
                        logout(request)
                        # Redirect to select_interests (user will be prompted to log in again)
                        return redirect('select_interests')
                    else:
                        messages.error(request, "Invalid OTP.")
                else:
                    messages.error(request, "OTP has expired.")
            else:
                messages.error(request, "No OTP found. Please request a new one.")
    
    # Check if user can request a new OTP
    can_request_otp = not profile.otp_created_at or timezone.now() - profile.otp_created_at > timedelta(minutes=1)
    
    return render(request, 'accounts/confirm_email.html', {
        'can_request_otp': can_request_otp,
        'profile': profile
    })
@login_required
def my_profile(request):
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    # Fetch user's recent posts (limited to 3)
    posts = Post.objects.filter(user=user, is_active=True).order_by('-created_at')[:3]
    
    # Attach first image to each post
    for post in posts:
        post.first_image = post.media_files.filter(media_type='image').first()
    
    # Fetch ever created events (limited to 3)
    events = Event.objects.filter(creator=user).order_by('start_time')[:3]
    
    # Fetch user's photos from posts (limited to 6)
    photos = Media.objects.filter(post__user=user, media_type='image').order_by('-created_at')[:6]
    
    # Fetch event images (limited to 6)
    event_images = EventImage.objects.filter(event__creator=user).order_by('-uploaded_at')[:6]
    
    # Calculate stats
    followers_count = Following.objects.filter(followed=profile).count()
    following_count = Following.objects.filter(follower=profile).count()
    posts_count = Post.objects.filter(user=user, is_active=True).count()
    events_count = Event.objects.filter(creator=user).count()
    
    context = {
        'profile': profile,
        'posts': posts,
        'events': events,
        'photos': photos,
        'event_images': event_images,
        'followers_count': followers_count,
        'following_count': following_count,
        'posts_count': posts_count,
        'events_count': events_count,
    }
    
    return render(request, 'accounts/myprofile.html', context)

@login_required
def edit_profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if request.method == 'POST':
        # Update User model fields
        user = request.user
        old_email = user.email
        old_username = user.username
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.username = request.POST.get('username', user.username)
        
        # Update UserProfile model fields
        old_bio = profile.bio
        profile.phone = request.POST.get('phone', profile.phone)
        profile.date_of_birth = request.POST.get('date_of_birth', profile.date_of_birth)
        profile.bio = request.POST.get('bio', profile.bio)
        
        try:
            user.save()
            profile.save()
            
            # Notify followers about significant profile updates
            followers = profile.followers
            if old_email != user.email or old_username != user.username or old_bio != profile.bio:
                for follower in followers:
                    Notification.objects.create(
                        recipient=follower.user,
                        message=f"{user.username} updated their profile",
                        link=reverse('my_profile'),
                        is_read=False
                    )
            
            messages.success(request, 'Profile updated successfully.')
            return redirect('my_profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    return render(request, 'accounts/myprofile.html', {'profile': profile})

@login_required
def my_event_list(request):
    events = Event.objects.filter(creator=request.user).order_by('-start_time')
    context = {'events': events}
    return render(request, 'accounts/myeventlist.html', context)

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.creator != request.user:
        raise PermissionDenied("You can only edit events you created.")

    errors = []
    all_interests = Interest.objects.all()

    if request.method == 'POST':
        # Extract and validate POST data
        title = request.POST.get('title')
        description = request.POST.get('description')
        category = request.POST.get('category')
        start_time_str = request.POST.get('start_time')
        end_time_str = request.POST.get('end_time')
        venue_name = request.POST.get('venue_name')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        interest_ids = request.POST.getlist('interests')
        max_attendees = request.POST.get('max_attendees')
        price = request.POST.get('price')
        registration_deadline_str = request.POST.get('registration_deadline')
        is_public = request.POST.get('is_public') == 'on'
        tags = request.POST.get('tags')

        # Validation
        if not title or len(title) > 200:
            errors.append("Title is required and must be 200 characters or less.")
        if not description:
            errors.append("Description is required.")
        if not category or category not in dict(Event.EVENT_CATEGORIES).keys():
            errors.append("Invalid category selected.")
        
        # Parse datetimes and make them offset-aware
        start_time = parse_datetime(start_time_str) if start_time_str else None
        end_time = parse_datetime(end_time_str) if end_time_str else None
        registration_deadline = parse_datetime(registration_deadline_str) if registration_deadline_str else None
        
        if start_time:
            start_time = timezone.make_aware(start_time, timezone=pytz.UTC)
        if end_time:
            end_time = timezone.make_aware(end_time, timezone=pytz.UTC)
        if registration_deadline:
            registration_deadline = timezone.make_aware(registration_deadline, timezone=pytz.UTC)
        
        if not start_time:
            errors.append("Valid start time is required.")
        if not end_time:
            errors.append("Valid end time is required.")
        if not registration_deadline:
            errors.append("Valid registration deadline is required.")
        
        if start_time and end_time and start_time >= end_time:
            errors.append("End time must be after start time.")
        if start_time and registration_deadline and registration_deadline > start_time:
            errors.append("Registration deadline must be before start time.")
        if start_time and start_time < timezone.now():
            errors.append("Start time cannot be in the past.")
        
        if not venue_name or len(venue_name) > 100:
            errors.append("Venue name is required and must be 100 characters or less.")
        
        try:
            latitude = Decimal(latitude) if latitude else None
            if latitude is None or latitude < -90 or latitude > 90:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Valid latitude between -90 and 90 is required.")
        
        try:
            longitude = Decimal(longitude) if longitude else None
            if longitude is None or longitude < -180 or longitude > 180:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Valid longitude between -180 and 180 is required.")
        
        try:
            max_attendees = int(max_attendees) if max_attendees else 0
            if max_attendees < 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Max attendees must be a non-negative integer.")
        
        try:
            price = Decimal(price) if price else 0
            if price < 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Price must be a non-negative number.")
        
        selected_interests = Interest.objects.filter(id__in=interest_ids)
        if not selected_interests.exists():
            errors.append("At least one interest must be selected.")
            
        # If no errors, update the event
        if not errors:
            # Store old values to check for significant changes
            old_title = event.title
            old_start_time = event.start_time
            old_venue_name = event.venue_name

            event.title = title
            event.description = description
            event.category = category
            event.start_time = start_time
            event.end_time = end_time
            event.venue_name = venue_name
            event.latitude = latitude
            event.longitude = longitude
            event.max_attendees = max_attendees
            event.price = price
            event.registration_deadline = registration_deadline
            event.is_public = is_public
            event.save()
            
            # Update interests
            event.interests.set(selected_interests)

            # Update tags
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                event.tags.set(tag_list)
            else:
                event.tags.clear()

            # Handle new images
            images = request.FILES.getlist('images')
            for image in images:
                EventImage.objects.create(
                    event=event,
                    image=image,
                    is_primary=(not event.images.exists())
                )

            # Notify attendees/invited users about significant event updates
            if old_title != title or old_start_time != start_time or old_venue_name != venue_name:
                # Get users who are attending or invited
                attending_users = User.objects.filter(attendance__event=event, attendance__status='attending')
                invited_users = User.objects.filter(invites__event=event)
                users_to_notify = (attending_users | invited_users).distinct().exclude(id=request.user.id)
                
                for user in users_to_notify:
                    Notification.objects.create(
                        recipient=user,
                        message=f"The event '{event.title}' has been updated",
                        link=reverse('view_event', kwargs={'event_id': event.id}),
                        is_read=False
                    )

            messages.success(request, "The event has been updated successfully!")
            return redirect('my_event_list')

    return render(request, 'accounts/edit_event.html', {
        'event': event,
        'all_interests': all_interests,
        'errors': errors
    })

@login_required
def remove_event_image(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_id = data.get('image_id')
        image = get_object_or_404(EventImage, id=image_id)
        if image.event.creator != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        image.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@login_required
def view_event(request, event_id):
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
    
    # Invite modal data (only for event creator)
    invited_users = []
    interest_aligned_users = []
    other_users = []
    if request.user == event.creator:
        # Group 1: Invited or Attending
        invited_users = UserProfile.objects.filter(
            user__attendance__event=event,
            user__attendance__status__in=['invited', 'attending', 'waiting_list']
        ).distinct().annotate(
            invite_sent=Count('user__invites', filter=Q(user__invites__event=event))
        )
        
        # Exclude invited users
        exclude_ids = invited_users.values_list('id', flat=True)
        
        # Group 2: Interest-Aligned (matching event interests)
        event_interests = set(event.interests.all())
        interest_aligned_users = UserProfile.objects.exclude(
            user=request.user
        ).exclude(
            id__in=exclude_ids
        ).filter(
            interests__in=event_interests
        ).annotate(
            shared_interests=Count('interests', filter=Q(interests__in=event_interests)),
            invite_sent=Count('user__invites', filter=Q(user__invites__event=event))
        ).order_by('-shared_interests')
        
        # Exclude interest-aligned users
        exclude_ids = list(exclude_ids) + list(interest_aligned_users.values_list('id', flat=True))
        
        # Group 3: Other Users
        other_users = UserProfile.objects.exclude(
            user=request.user
        ).exclude(
            id__in=exclude_ids
        ).annotate(
            invite_sent=Count('user__invites', filter=Q(user__invites__event=event))
        ).order_by('-user__date_joined')

    context = {
        'event': event,
        'attendance': attendance,
        'likes_count': likes_count,
        'user_has_liked': user_has_liked,
        'comments': comments,
        'invited_users': invited_users,
        'interest_aligned_users': interest_aligned_users,
        'other_users': other_users,
        'is_creator': request.user == event.creator,
    }
    return render(request, 'accounts/view_event.html', context)

@login_required
def send_invite(request, event_id):
    if request.method != 'POST':
        logger.warning(f"Invalid request method: {request.method}")
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

    event = get_object_or_404(Event, id=event_id)
    if request.user != event.creator:
        logger.warning(f"User {request.user.username} attempted to send invites for event {event_id} without permission")
        return JsonResponse({'success': False, 'message': 'Only the event creator can send invites.'}, status=403)

    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        if not user_ids:
            logger.warning("No user IDs provided in send_invite request")
            return JsonResponse({'success': False, 'message': 'No users selected.'}, status=400)

        subject = f"You're Invited to {event.title} on myVibe!"
        from_email = "invites@myvibe.com"
        domain = get_current_site(request).domain
        results = []

        for user_id in user_ids:
            try:
                recipient = get_object_or_404(UserProfile, user__id=user_id)
                if not recipient.user.email:
                    results.append({'user_id': user_id, 'success': False, 'message': 'User has no email address'})
                    continue

                if Invite.objects.filter(event=event, recipient=recipient.user).exists():
                    results.append({'user_id': user_id, 'success': False, 'message': 'Invite already sent'})
                    continue

                try:
                    html_content = render_to_string('accounts/event_email.html', {
                        'event': event,
                        'recipient': recipient.user,
                        'domain': f'http://{domain}',
                    })
                except Exception as e:
                    results.append({'user_id': user_id, 'success': False, 'message': f'Template rendering failed: {str(e)}'})
                    continue

                try:
                    email = EmailMessage(subject, html_content, from_email, [recipient.user.email])
                    email.content_subtype = "html"
                    email.send(fail_silently=False)
                except Exception as e:
                    results.append({'user_id': user_id, 'success': False, 'message': f'Email sending failed: {str(e)}'})
                    continue

                try:
                    invite = Invite.objects.create(event=event, recipient=recipient.user)
                    # Notify the recipient about the invite
                    Notification.objects.create(
                        recipient=recipient.user,
                        message=f"You've been invited to the event '{event.title}' by {request.user.username}",
                        link=reverse('view_event', kwargs={'event_id': event.id}),
                        is_read=False
                    )
                    results.append({'user_id': user_id, 'success': True, 'message': 'Invite sent successfully'})
                except Exception as e:
                    results.append({'user_id': user_id, 'success': False, 'message': f'Failed to save invite: {str(e)}'})
                    continue

            except Exception as e:
                results.append({'user_id': user_id, 'success': False, 'message': f'Error processing user: {str(e)}'})

        sent_count = sum(1 for result in results if result['success'])
        if sent_count == 0:
            logger.info("No new invites sent; all users already invited or had errors")
            return JsonResponse({'success': False, 'message': 'No new invites sent.', 'results': results}, status=200)

        messages.success(request, f"Invites sent successfully to {sent_count} user(s).")
        logger.info(f"Sent {sent_count} invites for event {event_id} by user {request.user.username}")
        return JsonResponse({'success': True, 'message': f'Invites sent to {sent_count} user(s).', 'results': results})
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in send_invite request: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Invalid request data.'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in send_invite for event {event_id}: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Unexpected error: {str(e)}'}, status=500)

@login_required
@csrf_exempt
def update_theme(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            theme = data.get('theme')
            logger.debug(f'Received theme update request: {data}')
            if theme not in ['light', 'dark']:
                logger.error(f'Invalid theme value: {theme}')
                return JsonResponse({'success': False, 'error': 'Invalid theme value'}, status=400)
            if not hasattr(request.user, 'userprofile'):
                logger.error('User has no UserProfile')
                return JsonResponse({'success': False, 'error': 'User profile not found'}, status=400)
            request.user.userprofile.theme = theme
            request.user.userprofile.save()
            logger.info(f'Theme updated for user {request.user.username}: {theme}')
            return JsonResponse({'success': True})
        except json.JSONDecodeError as e:
            logger.error(f'JSON decode error: {str(e)}')
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f'Unexpected error: {str(e)}')
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    logger.warning(f'Invalid request method: {request.method}')
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@login_required
def select_interests(request):
    # Redirect if the user already has interests
    if request.user.userprofile.interests.exists():
        return redirect('update_profile_picture')  # Redirect to profile picture upload if interests already set
    
    if request.method == 'POST':
        # Retrieve list of selected interest IDs from the POST data
        selected_ids = request.POST.getlist('interests')
        # Query the Interest objects
        selected_interests = Interest.objects.filter(id__in=selected_ids)
        # Save to the user's profile (ManyToManyField)
        request.user.userprofile.interests.set(selected_interests)
        return redirect('update_profile_picture')  # Redirect to profile picture upload after saving interests
    
    # For GET, provide a sample of 12 interests and all interests for search
    all_interests = Interest.objects.all()
    sample_interests = all_interests.order_by('?')[:12]  # Randomly select 12 interests
    return render(request, 'accounts/select_interests.html', {
        'sample_interests': sample_interests,
        'all_interests': all_interests,
        'username': request.user.username
    })
    
    
def logout_view(request):
    logout(request)
    return redirect('home')

def user_profile(request):
    """Load and update user profile information"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Load user data on GET request
    if request.method == 'GET':
        try:
            # Get the user's profile
            user_profile = request.user.userprofile

            # If the user has a profile, populate the context with their details
            context = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'username': request.user.username,
                'email': request.user.email,
                'phone': user_profile.phone,
                'date_of_birth': user_profile.date_of_birth,
                'gender': user_profile.gender,
                'profile_picture': user_profile.profile_picture.url if user_profile.profile_picture else static('assets/img/default_dp.png')
            }

            return render(request, 'accounts/userprofile.html', context)

        except UserProfile.DoesNotExist:
            context = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'username': request.user.username,
                'email': request.user.email,
                'phone': '',
                'date_of_birth': '',
                'gender': '',
                'profile_picture': 'https://bootdey.com/img/Content/avatar/avatar1.png'
            }

            return render(request, 'accounts/userprofile.html', context)

    # Handle form submission on POST request
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')

        # Check if a new profile picture was uploaded
        profile_picture = request.FILES.get('profile_picture')

        # Update user object and save
        user = request.user
        old_email = user.email
        old_username = user.username
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.email = email

        # Check if the user has a related UserProfile
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        # Update users profile
        old_bio = user_profile.bio
        user_profile.phone = phone
        user_profile.date_of_birth = date_of_birth
        user_profile.gender = gender
        user_profile.bio = old_bio  # Since bio isn't in the form, preserve it

        # If a new profile picture is provided, update it
        if profile_picture:
            user_profile.profile_picture = profile_picture

        # Save changes to both user and profile models
        user.save()
        user_profile.save()

        # Notify followers about significant profile updates
        if old_email != user.email or old_username != user.username or (profile_picture and profile_picture != user_profile.profile_picture):
            followers = user_profile.followers
            for follower in followers:
                Notification.objects.create(
                    recipient=follower.user,
                    message=f"{user.username} updated their profile",
                    link=reverse('user_profile'),
                    is_read=False
                )

        messages.success(request, 'Profile updated successfully' if not created else 'Profile created successfully')
        return redirect('user_profile')

    return render(request, 'accounts/userprofile.html')

@login_required
def profile_picture_upload(request):
    try:
        user_profile = request.user.userprofile
        if user_profile.profile_picture:
            profile_picture_url = user_profile.profile_picture.url
        else:
            profile_picture_url = finders.find('assets/img/upload.png')
    except UserProfile.DoesNotExist:
        profile_picture_url = finders.find('assets/img/upload.png')
    
    return render(request, 'accounts/upload_image.html', {'profile_picture_url': profile_picture_url})

@login_required
def update_profile_picture(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        profile_picture = request.FILES.get('profile_picture')
        
        if not profile_picture:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        
        if not profile_picture.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'Invalid file type'})
        
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'phone': ''}
        )
        
        user_profile.profile_picture = profile_picture
        user_profile.save()
        
        followers = user_profile.followers
        for follower in followers:
            Notification.objects.create(
                recipient=follower.user,
                message=f"{request.user.username} updated their profile picture",
                link=reverse('user_profile'),
                is_read=False
            )
        
        return JsonResponse({
            'success': True,
            'url': user_profile.profile_picture.url
        })
    
    # Redirect to profile_picture_upload instead of itself
    return redirect('upload_image')


@login_required
def follow_user(request, username):
    user_to_follow = get_object_or_404(User, username=username)
    if user_to_follow == request.user:
        messages.error(request, "You cannot follow yourself.")
        return redirect('user_profile')
    
    profile = request.user.userprofile
    target_profile = user_to_follow.userprofile
    
    if profile.is_following(target_profile):
        messages.info(request, f"You are already following {username}.")
    else:
        profile.follow(target_profile)
        # Notify the user being followed
        Notification.objects.create(
            recipient=user_to_follow,
            message=f"{request.user.username} started following you",
            link=reverse('user_profile'),
            is_read=False
        )
        messages.success(request, f"You are now following {username}.")
    
    return redirect('user_profile')

@login_required
def unfollow_user(request, username):
    user_to_unfollow = get_object_or_404(User, username=username)
    if user_to_unfollow == request.user:
        messages.error(request, "You cannot unfollow yourself.")
        return redirect('user_profile')
    
    profile = request.user.userprofile
    target_profile = user_to_unfollow.userprofile
    
    if not profile.is_following(target_profile):
        messages.info(request, f"You are not following {username}.")
    else:
        profile.unfollow(target_profile)
        # Notify the user being unfollowed
        Notification.objects.create(
            recipient=user_to_unfollow,
            message=f"{request.user.username} unfollowed you",
            link=reverse('user_profile'),
            is_read=False
        )
        messages.success(request, f"You have unfollowed {username}.")
    
    return redirect('user_profile')

def choose_interests(request):
    # Check if the user has clicked one of the interests (passed as GET parameter)
    selected_id = request.GET.get('selected')
    if selected_id:
        try:
            selected_interest = Interest.objects.get(id=selected_id)
            # Fetch related interests for the selected interest
            related_interests = list(selected_interest.related_interests.all())
        except Interest.DoesNotExist:
            related_interests = []
    else:
        related_interests = []

    # Fetch all interests
    all_interests = list(Interest.objects.all())

    # Remove any interests already in the related_interests to avoid duplicates
    remaining_interests = [i for i in all_interests if i not in related_interests]

    # Prioritize: Place related interests first, then the remaining interests
    prioritized_interests = related_interests + remaining_interests

    # Limit to a maximum of 15 interests
    interests_to_display = prioritized_interests[:15]

    context = {
        'interests': interests_to_display,
        'selected_interest': selected_id,  # so the template can show which one was clicked
    }
    return render(request, 'accounts/choose_interests.html', context)

@login_required
def admin_dashboard(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")
    return render(request, 'admin_dashboard.html')

@login_required
def notifications(request):
    # Get all notifications for the user
    user_notifications = Notification.objects.filter(recipient=request.user)
    
    # Mark unread notifications as read when the page is viewed
    unread_notifications = user_notifications.filter(is_read=False)
    if unread_notifications.exists():
        unread_notifications.update(is_read=True)
    
    return render(request, 'accounts/notifications.html', {
        'notifications': user_notifications
    })
    
@login_required
@require_POST
@csrf_exempt
def toggle_notification_read(request):
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        is_read = data.get('is_read')
        
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.is_read = is_read
        notification.save()
        
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'success': True, 'unread_count': unread_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
@csrf_exempt
def delete_notification(request):
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.delete()
        
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'success': True, 'unread_count': unread_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
@csrf_exempt
def clear_notifications(request):
    try:
        Notification.objects.filter(recipient=request.user).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)