from django.contrib import admin
from .models import StudyGroup, GroupMembership, JoinRequest, PostApproval, GroupMessage, Notification

@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'group_type', 'access_type', 'created_at')
    list_filter = ('group_type', 'access_type')

@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'joined_at')

@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'status', 'created_at')

@admin.register(PostApproval)
class PostApprovalAdmin(admin.ModelAdmin):
    list_display = ('post', 'group', 'submitted_by', 'status', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')
