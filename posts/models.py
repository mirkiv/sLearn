from django.db import models
from django.conf import settings
from groups.models import StudyGroup

class Hashtag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return f"#{self.name}"

class Post(models.Model):
    POST_TYPES = (
        ('note', 'Конспект'),
        ('standard', 'Обычный пост'),
        ('question', 'Вопрос'),
    )
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private')
    )
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='standard')
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True, help_text="Body content for standard or question posts.")
    hashtags = models.ManyToManyField(Hashtag, related_name='posts')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='group_posts', null=True, blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Post by {self.author.username}"

class NoteChapter(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200, blank=True)
    text_content = models.TextField(blank=True)
    image = models.ImageField(upload_to='post_chapter_images/', null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class Attachment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='post_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
