from django.urls import path
from . import views

app_name = 'groups'
urlpatterns = [
    path('', views.group_list, name='list'),
    path('create/', views.group_create, name='create'),
    path('<int:pk>/', views.group_detail, name='detail'),
    path('<int:pk>/join/', views.group_join, name='join'),
    path('<int:pk>/leave/', views.group_leave, name='leave'),
    path('<int:pk>/settings/', views.group_settings, name='settings'),
    path('<int:pk>/add-note/', views.add_note_to_group, name='add_note'),
    path('<int:pk>/join-request/<int:request_id>/<str:action>/', views.handle_join_request, name='handle_join_request'),
    path('<int:pk>/submit-review/<int:post_id>/', views.submit_for_review, name='submit_for_review'),
    path('<int:pk>/review/<int:approval_id>/<str:action>/', views.review_post, name='review_post'),
    path('<int:pk>/api/messages/', views.api_group_messages, name='api_group_messages'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/read/', views.api_mark_notifications_read, name='api_mark_notifications_read'),
    path('api/notifications/<int:notif_id>/read/', views.api_mark_notification_read_single, name='api_mark_notification_read_single'),
    path('<int:pk>/messenger/', views.group_messenger, name='messenger'),
    path('api/messages/<int:message_id>/delete/', views.api_delete_group_message, name='api_delete_group_message'),
]
