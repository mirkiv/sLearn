from django.urls import path
from . import views

app_name = 'chat'
urlpatterns = [
    path('', views.chat_list, name='list'),
    path('api/forward/bulk/', views.api_bulk_forward, name='api_bulk_forward'),
    path('api/react/<int:message_id>/', views.api_add_reaction, name='api_react'),
    path('api/delete/<int:message_id>/', views.api_delete_message, name='api_delete'),
    path('api/<str:username>/messages/', views.api_messages, name='api_messages'),
    path('<str:username>/', views.chat_detail, name='detail'),
]
