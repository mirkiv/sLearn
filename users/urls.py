from django.urls import path
from . import views

app_name = 'users'
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('saved/', views.saved_posts_view, name='saved_posts'),
    path('search/', views.search_users, name='search'),
    path('follow/<str:username>/', views.toggle_follow, name='toggle_follow'),
    path('<str:username>/', views.user_detail, name='user_detail'),
    path('set-lang/<str:base_lang>/', views.set_language, name='set_language'),
]
