from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # AbstractUser includes username, email, password, etc.
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    saved_posts = models.ManyToManyField('posts.Post', related_name='saved_by', blank=True)
    
    def __str__(self):
        return self.username
