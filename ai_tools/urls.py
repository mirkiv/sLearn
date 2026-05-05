from django.urls import path
from . import views

app_name = 'ai_tools'
urlpatterns = [
    path('', views.ai_dashboard, name='combine'),
    path('save_as_note/', views.save_as_note, name='save_as_note'),
    path('<str:provider>/', views.ai_provider_view, name='provider_view'),
    path('<str:provider>/validate/', views.validate_api_key, name='validate_api_key'),
    path('<str:provider>/settings/', views.provider_settings, name='settings'),
    path('<str:provider>/combine_action/', views.combine_notes_action, name='combine_action'),
]
