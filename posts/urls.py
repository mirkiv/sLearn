from django.urls import path
from . import views

app_name = 'posts'
urlpatterns = [
    path('', views.post_list, name='list'),
    path('create/', views.post_create, name='create'),
    path('<int:pk>/', views.post_detail, name='detail'),
    path('<int:pk>/edit/', views.post_edit, name='edit'),
    path('<int:pk>/add-chapter/', views.add_chapter, name='add_chapter'),
    path('<int:pk>/save/', views.toggle_save, name='toggle_save'),
    path('<int:pk>/delete/', views.post_delete, name='delete'),
    path('upload/', views.upload_file, name='upload_file'),
]
