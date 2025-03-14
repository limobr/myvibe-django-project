from django.urls import path
from . import views

urlpatterns = [
    path('create-event/', views.create_event, name='create_event'),
    path('', views.events_view, name='events_view'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
]