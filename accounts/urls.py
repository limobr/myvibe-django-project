from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('confirm-email/', views.confirm_email, name='confirm_email'),
    path('select-interests/', views.select_interests, name='select_interests'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    path('user/', views.user_profile, name='user_profile'),
    path('upload/', views.profile_picture_upload, name='upload_image'),
    path('update-profile-picture/', views.update_profile_picture, name='update_profile_picture'),
    path('update-theme/', views.update_theme, name='update_theme'),
    path('myprofile/', views.my_profile, name='my_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('myevents/', views.my_event_list, name='my_event_list'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/remove-image/', views.remove_event_image, name='remove_event_image'),
    path('events/<int:event_id>/', views.view_event, name='view_event'),
    path('event/<int:event_id>/invite/', views.send_invite, name='send_invite'),
    path('notifications/', views.notifications, name='notifications'),
    path('toggle-notification-read/', views.toggle_notification_read, name='toggle_notification_read'),
    path('delete-notification/', views.delete_notification, name='delete_notification'),
    path('clear-notifications/', views.clear_notifications, name='clear_notifications'),
]