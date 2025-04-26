from django.urls import path
from . import views

urlpatterns = [
    path('administration/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('administration/interests/', views.view_interests, name='view_interests'),
    path('administration/interests/edit/', views.edit_interest, name='edit_interest'),
    path('administration/interests/delete/', views.delete_interest, name='delete_interest'),
    path('administration/interests/add/', views.add_interest, name='add_interest'),
    
    ####################################### users #############################################
    path('', views.home_view, name='home'),
    path('create-post/', views.create_post, name='create_post'),
    path('post/<int:post_id>/details/', views.post_detail_modal, name='post_detail_modal'),
    path('add-comment/', views.add_comment, name='add_comment'),
    path('discover/', views.discover_users, name='discover_users'),
    path('follow/', views.follow_user, name='follow_user'),
]