from django.db import models
from django.conf import settings


class StudyGroup(models.Model):
    GROUP_TYPE_CHOICES = (
        ('moderated', 'Moderated'),
        ('open', 'Open'),
    )
    ACCESS_TYPE_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, default='open')
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPE_CHOICES, default='public')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def owner(self):
        m = self.memberships.filter(role='teacher').first()
        return m.user if m else None


class GroupMembership(models.Model):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"


class JoinRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='join_requests')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='join_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} -> {self.group.name} ({self.status})"


class PostApproval(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, related_name='approvals')
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='approvals')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_approvals')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='reviewed_approvals')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Approval for '{self.post.title}' in {self.group.name} ({self.status})"


class GroupMessage(models.Model):
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_messages')
    text = models.TextField(blank=True, default='')
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} in {self.group.name}"


class Notification(models.Model):
    NOTIF_TYPES = (
        ('join_request', 'Join Request'),
        ('join_accepted', 'Join Accepted'),
        ('join_rejected', 'Join Rejected'),
        ('post_approved', 'Post Approved'),
        ('post_rejected', 'Post Rejected'),
        ('new_follower', 'New Follower'),
        ('follow_request', 'Follow Request'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='actions', null=True, blank=True)
    notif_type = models.CharField(max_length=30, choices=NOTIF_TYPES)
    title = models.CharField(max_length=255, blank=True) # Now optional
    message = models.TextField(blank=True) # Now optional
    extra_data = models.JSONField(default=dict, blank=True)
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notif_type}] {self.title} -> {self.user.username}"

class GroupMessageAttachment(models.Model):
    message = models.ForeignKey(GroupMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='group_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
