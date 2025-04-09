from django.urls import path
from . import views

urlpatterns = [
    path('create-event/', views.create_event, name='create_event'),
    path('', views.events_view, name='events_view'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('event/<int:event_id>/like/', views.like_event, name='like_event'),
    path('event/<int:event_id>/share/', views.share_event, name='share_event'),
    path('event/<int:event_id>/comment/', views.add_comment, name='add_comment'),
    path('event/<int:event_id>/attend/', views.join_waiting_list, name='join_waiting_list'),  # Note: Fixed typo from 'join industriawaiting_list'
    path('event/<int:event_id>/accept_invite/', views.accept_invite, name='accept_invite'),
]