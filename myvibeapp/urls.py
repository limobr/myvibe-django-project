from django.urls import path
from . import views

urlpatterns = [
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/interests/', views.view_interests, name='view_interests'),
    path('admin/interests/edit/', views.edit_interest, name='edit_interest'),
    path('admin/interests/delete/', views.delete_interest, name='delete_interest'),
    path('admin/interests/add/', views.add_interest, name='add_interest'),
    
    ####################################### users #############################################
    path('', views.home_view, name='home'),
    path('create-post/', views.create_post, name='create_post'),
]
