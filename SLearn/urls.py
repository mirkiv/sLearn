from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from posts.views import feed_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('groups/', include('groups.urls')),
    path('posts/', include('posts.urls')),
    path('chat/', include('chat.urls')),
    path('ai/', include('ai_tools.urls')),
    path('', feed_view, name='home'),
]

handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

from django.urls import re_path
from chat.views import serve_media
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media),
]
