from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('confirm-email/', views.confirm_email, name='confirm_email'),
    path('select-interests/', views.select_interests, name='select_interests'),
    path('logout/', views.logout_view, name='logout'),
    path('user/', views.user_profile, name='user_profile'),
    path('upload/', views.profile_picture_upload, name='upload_image'),
    path('update-profile-picture/', views.update_profile_picture, name='update_profile_picture'),
    path('update-theme/', views.update_theme, name='update_theme'),
]