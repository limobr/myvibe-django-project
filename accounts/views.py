from datetime import time
from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Interest, UserProfile
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import logging
import json

def register(request):
    """Show the registration form and handle user registration"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Check if passwords match
        if password == confirm_password:
            # Check if username or email already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email already in use')
            else:
                # Create the user if validation passes
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
                # If the profile already existed, you can update its usertype if necessary.
                if not created:
                    user_profile.usertype = 'user'
                    user_profile.save()

                messages.success(request, "Account created successfully")
                return redirect('home')
        else:
            messages.error(request, 'Passwords do not match')

    return render(request, 'accounts/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
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
    
    return render(request, 'accounts/login.html')

def generate_otp():
    return str(random.randint(100000, 999999))

def confirm_email(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    profile = request.user.userprofile  # Assuming a UserProfile model linked to User
    
    if request.method == 'POST':
        if 'request_otp' in request.POST:
            # Check if a new OTP can be requested (1-minute cooldown)
            if not profile.otp_created_at or timezone.now() - profile.otp_created_at > timedelta(minutes=1):
                otp = generate_otp()  # Assuming this function generates a 6-digit OTP
                profile.otp_code = otp
                profile.otp_created_at = timezone.now()
                profile.save()
                
                # Prepare email content
                subject = "Verify Your Email Address for myVibe"
                from_email = "verification@myvibe.com"  # Recognizable "From" address
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
                email.content_subtype = "html"  # Set content type to HTML
                email.send(fail_silently=False)
                
                messages.info(request, "OTP has been sent to your email.")
            else:
                messages.info(request, "Please wait 1 minute before requesting a new OTP.")
        elif 'verify_otp' in request.POST:
            entered_otp = request.POST.get('otp')
            if profile.otp_code and profile.otp_created_at:
                if timezone.now() - profile.otp_created_at < timedelta(hours=2):
                    if entered_otp == profile.otp_code:
                        profile.email_confirmed = True
                        profile.otp_code = None
                        profile.otp_created_at = None
                        profile.save()
                        messages.success(request, "Your email has been confirmed!")
                        return redirect('home')
                    else:
                        messages.error(request, "Invalid OTP.")
                else:
                    messages.error(request, "OTP has expired.")
            else:
                messages.error(request, "No OTP found. Please request a new one.")
    
    # Check if user can request a new OTP
    can_request_otp = not profile.otp_created_at or timezone.now() - profile.otp_created_at > timedelta(minutes=1)
    
    return render(request, 'accounts/confirm_email.html', {'can_request_otp': can_request_otp})

logger = logging.getLogger(__name__)

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
        return redirect('home')
    
    if request.method == 'POST':
        # Retrieve list of selected interest IDs from the POST data
        selected_ids = request.POST.getlist('interests')
        # Query the Interest objects
        selected_interests = Interest.objects.filter(id__in=selected_ids)
        # Save to the user's profile (ManyToManyField)
        request.user.userprofile.interests.set(selected_interests)
        return redirect('home')
    
    # For GET, display all available interests
    interests = Interest.objects.all()
    return render(request, 'accounts/select_interests.html', {'interests': interests, 'username': request.user.username})

def logout_view(request):
    logout(request)
    return redirect('home')


def user_profile(request):
    """Load and update user profile information"""
    
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
                'profile_picture': user_profile.profile_picture.url if user_profile.profile_picture else static('assets/img/default_dp.png')  # Default picture
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
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.email = email

        # Check if the user has a related UserProfile
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        # update users profile
        user_profile.phone = phone
        user_profile.date_of_birth = date_of_birth
        user_profile.gender = gender

        # If a new profile picture is provided, update it
        if profile_picture:
            user_profile.profile_picture = profile_picture

        # Save changes to both user and profile models
        user.save()
        user_profile.save()

        messages.success(request, 'Profile updated successfully' if not created else 'Profile created successfully')
        return redirect('user_profile')  # Redirect to the same page to show changes

    return render(request, 'accounts/userprofile.html')


    


@login_required
def profile_picture_upload(request):
    try:
        user_profile = request.user.userprofile
        if user_profile.profile_picture:
            profile_picture_url = user_profile.profile_picture.url
        else:
            profile_picture_url = static('assets/img/upload.png')
    except UserProfile.DoesNotExist:
        profile_picture_url = static('assets/img/upload.png')
    
    return render(request, 'accounts/upload_image.html', {'profile_picture_url': profile_picture_url})

@login_required
def update_profile_picture(request):
    """
    Handle the AJAX POST request to update the user's profile picture with the cropped image.
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        profile_picture = request.FILES.get('profile_picture')
        
        if not profile_picture:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
        
        # Validate that the file is an image
        if not profile_picture.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'Invalid file type'})
        
        # Get or create the UserProfile instance for the authenticated user
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'phone': ''}  # Default phone value if profile is created
        )
        
        # Assign the cropped image to the profile_picture field
        user_profile.profile_picture = profile_picture
        user_profile.save()
        
        # Return a JSON response with the success status and the URL of the saved image
        return JsonResponse({
            'success': True,
            'url': user_profile.profile_picture.url
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def choose_interests(request):
    # Check if the user has clicked one of the interests (passed as GET parameter)
    selected_id = request.GET.get('selected')
    if selected_id:
        try:
            selected_interest = Interest.objects.get(id=selected_id)
            # Fetch related interests for the selected interest.
            related_interests = list(selected_interest.related_interests.all())
        except Interest.DoesNotExist:
            related_interests = []
    else:
        related_interests = []

    # Fetch all interests
    all_interests = list(Interest.objects.all())

    # Remove any interests already in the related_interests to avoid duplicates
    remaining_interests = [i for i in all_interests if i not in related_interests]

    # Prioritize: Place related interests first, then the remaining interests.
    prioritized_interests = related_interests + remaining_interests

    # Limit to a maximum of 15 interests.
    interests_to_display = prioritized_interests[:15]

    context = {
        'interests': interests_to_display,
        'selected_interest': selected_id,  # so the template can show which one was clicked
    }
    return render(request, 'accounts/choose_interests.html', context)

@login_required
def admin_dashboard(request):
    # Ensure the logged in user has an associated UserProfile with admin usertype.
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.usertype != 'admin':
        return HttpResponseForbidden("You are not authorized to view this page.")
    return render(request, 'admin_dashboard.html')