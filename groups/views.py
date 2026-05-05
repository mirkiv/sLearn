from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
import re, os
from .models import StudyGroup, GroupMembership, JoinRequest, PostApproval, GroupMessage, Notification
from posts.templatetags.custom_dict import t_py
from chat.views import get_chat_sidebar_data


@login_required
def group_list(request):
    groups = StudyGroup.objects.all().order_by('-created_at')
    user_groups = set(request.user.memberships.values_list('group_id', flat=True))
    pending_requests = set(JoinRequest.objects.filter(user=request.user, status='pending').values_list('group_id', flat=True))
    return render(request, 'groups/list.html', {
        'groups': groups,
        'user_groups': user_groups,
        'pending_requests': pending_requests,
    })


@login_required
def group_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        group_type = request.POST.get('group_type', 'open')
        access_type = request.POST.get('access_type', 'public')
        if name:
            group = StudyGroup.objects.create(
                name=name,
                description=description,
                group_type=group_type,
                access_type=access_type,
            )
            GroupMembership.objects.create(user=request.user, group=group, role='teacher')
            return redirect('groups:detail', pk=group.pk)
    return render(request, 'groups/create.html')


@login_required
def group_detail(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    members = group.memberships.select_related('user').all()

    if group.group_type == 'moderated':
        notes = group.group_posts.filter(
            post_type='note',
            approvals__status='approved'
        ).distinct()
    else:
        notes = group.group_posts.filter(post_type='note')

    pending_approvals = []
    is_owner = membership and membership.role == 'teacher'
    if is_owner and group.group_type == 'moderated':
        pending_approvals = PostApproval.objects.filter(group=group, status='pending').select_related('post', 'submitted_by')

    join_requests = []
    if is_owner and group.access_type == 'private':
        join_requests = JoinRequest.objects.filter(group=group, status='pending').select_related('user')

    pending_join = JoinRequest.objects.filter(user=request.user, group=group, status='pending').exists()

    context = {
        'group': group,
        'membership': membership,
        'members': members,
        'notes': notes,
        'is_owner': is_owner,
        'pending_approvals': pending_approvals,
        'join_requests': join_requests,
        'pending_join': pending_join,
    }
    return render(request, 'groups/detail.html', context)


@login_required
def group_join(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    if GroupMembership.objects.filter(user=request.user, group=group).exists():
        return redirect('groups:detail', pk=group.pk)

    if group.access_type == 'private':
        jr, created = JoinRequest.objects.get_or_create(user=request.user, group=group)
        # If it's a new request OR a previous request that wasn't pending (e.g. was accepted/rejected before)
        if created or jr.status != 'pending':
            jr.status = 'pending'
            jr.save()
            
            owner = group.owner()
            if owner:
                Notification.objects.create(
                    user=owner,
                    actor=request.user,
                    notif_type='join_request',
                    extra_data={'group_name': group.name},
                    link=f'/groups/{group.pk}/',
                )
    else:
        GroupMembership.objects.create(user=request.user, group=group, role='student')

    return redirect('groups:detail', pk=group.pk)


@login_required
def handle_join_request(request, pk, request_id, action):
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='teacher').first()
    if not membership:
        return redirect('groups:detail', pk=pk)

    jr = get_object_or_404(JoinRequest, pk=request_id, group=group)

    if action == 'accept':
        jr.status = 'accepted'
        jr.save()
        GroupMembership.objects.get_or_create(user=jr.user, group=group, defaults={'role': 'student'})
        Notification.objects.create(
            user=jr.user,
            actor=request.user,
            notif_type='join_accepted',
            extra_data={'group_name': group.name},
            link=f'/groups/{group.pk}/',
        )
    elif action == 'reject':
        jr.status = 'rejected'
        jr.save()
        Notification.objects.create(
            user=jr.user,
            actor=request.user,
            notif_type='join_rejected',
            extra_data={'group_name': group.name},
            link=f'/groups/{group.pk}/',
        )

    return redirect('groups:detail', pk=pk)


@login_required
def group_settings(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='teacher').first()
    if not membership:
        return redirect('groups:detail', pk=pk)

    if request.method == 'POST':
        group.name = request.POST.get('name', group.name).strip()
        group.description = request.POST.get('description', group.description).strip()
        group.group_type = request.POST.get('group_type', group.group_type)
        group.access_type = request.POST.get('access_type', group.access_type)
        group.save()
        return redirect('groups:detail', pk=pk)

    return render(request, 'groups/settings.html', {'group': group})


@login_required
def submit_for_review(request, pk, post_id):
    from posts.models import Post
    group = get_object_or_404(StudyGroup, pk=pk)
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    if not membership or group.group_type != 'moderated':
        return redirect('groups:detail', pk=pk)

    PostApproval.objects.get_or_create(
        post=post, group=group, submitted_by=request.user,
        defaults={'status': 'pending'}
    )

    owner = group.owner()
    if owner:
        o_lang = getattr(owner, 'theme_preference', 'ru')
        Notification.objects.create(
            user=owner,
            actor=request.user,
            notif_type='post_approved', # Reusing post_approved type but extra_data identifies it as review request
            extra_data={'post_title': post.title, 'group_name': group.name},
            link=f'/groups/{group.pk}/',
        )

    return redirect('groups:detail', pk=pk)


@login_required
def review_post(request, pk, approval_id, action):
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='teacher').first()
    if not membership:
        return redirect('groups:detail', pk=pk)

    approval = get_object_or_404(PostApproval, pk=approval_id, group=group)
    comment = request.POST.get('comment', '').strip()

    if action == 'approve':
        approval.status = 'approved'
        approval.reviewed_by = request.user
        approval.comment = comment
        approval.reviewed_at = timezone.now()
        approval.save()
        Notification.objects.create(
            user=approval.submitted_by,
            actor=request.user,
            notif_type='post_approved',
            extra_data={'post_title': approval.post.title, 'comment': comment},
            link=f'/posts/{approval.post.pk}/',
        )
    elif action == 'reject':
        approval.status = 'rejected'
        approval.reviewed_by = request.user
        approval.comment = comment
        approval.reviewed_at = timezone.now()
        approval.save()
        Notification.objects.create(
            user=approval.submitted_by,
            actor=request.user,
            notif_type='post_rejected',
            extra_data={'post_title': approval.post.title, 'group_name': group.name, 'comment': comment},
            link=f'/posts/{approval.post.pk}/',
        )

    return redirect('groups:detail', pk=pk)


# --- Group Chat API ---

@login_required
def api_group_messages(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    lang = request.session.get('lang', 'ru')
    if not membership:
        return JsonResponse({'status': 'error', 'message': t_py('error_not_member', lang)}, status=403)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        files = request.FILES.getlist('file')
        reply_to_id = request.POST.get('reply_to_id')
        
        reply_to = None
        if reply_to_id:
            reply_to = GroupMessage.objects.filter(id=reply_to_id).first()

        if text or files:
            msg = GroupMessage.objects.create(group=group, sender=request.user, text=text, reply_to=reply_to)
            for f in files:
                from .models import GroupMessageAttachment
                GroupMessageAttachment.objects.create(message=msg, file=f)
        return JsonResponse({'status': 'ok'})

    after_id = int(request.GET.get('after_id', 0))
    messages = group.messages.filter(id__gt=after_id).select_related('sender', 'reply_to').prefetch_related('attachments')[:100]
    data = []
    for msg in messages:
        avatar_url = msg.sender.avatar.url if msg.sender.avatar else None
        
        attachments = []
        for att in msg.attachments.all():
            raw_name = os.path.basename(att.file.name)
            clean_name = re.sub(r'^[0-9a-f]{32,}_', '', raw_name)
            is_img = any(att.file.name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
            attachments.append({
                'url': att.file.url,
                'name': clean_name,
                'is_image': is_img
            })

        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'avatar': avatar_url,
            'text': msg.text,
            'attachments': attachments,
            'reply_to_id': msg.reply_to.id if msg.reply_to else None,
            'reply_to_text': msg.reply_to.text[:50] if msg.reply_to else None,
            'reply_to_user': msg.reply_to.sender.username if msg.reply_to else None,
            # Legacy fields for UI compatibility
            'file_url': attachments[0]['url'] if attachments else None,
            'file_name': attachments[0]['name'] if attachments else None,
            'is_image': attachments[0]['is_image'] if attachments else False,
            'created_at': msg.created_at.strftime('%H:%M'),
        })
    return JsonResponse({'status': 'ok', 'messages': data})

@login_required
def group_messenger(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    if not membership:
        return redirect('groups:list')
        
    other_groups = StudyGroup.objects.filter(memberships__user=request.user).exclude(pk=pk).distinct()
    
    recent_users, user_groups = get_chat_sidebar_data(request.user)
    
    return render(request, 'chat/messenger.html', {
        'recent_users': recent_users,
        'user_groups': user_groups,
        'active_group': group,
        'active_chat': None,
    })


# --- Notifications API ---

@login_required
def api_notifications(request):
    from chat.models import Message
    notifs = request.user.notifications.all().select_related('actor')[:20]
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    # Check for unread messenger messages
    unread_msgs = Message.objects.filter(receiver=request.user, is_read=False)
    unread_msgs_count = unread_msgs.count()
    last_msg = unread_msgs.order_by('-created_at').first()
    
    msg_data = None
    if last_msg:
        msg_data = {
            'sender': last_msg.sender.username,
            'text': last_msg.text[:50] + ('...' if len(last_msg.text) > 50 else ''),
        }

    data = []
    lang = request.session.get('lang', 'ru')
    for n in notifs:
        actor_name = n.actor.username if n.actor else "System"
        extra = n.extra_data or {}
        
        # Dynamic rendering
        title, message = n.title, n.message # Fallbacks
        
        # If it's a new-style notification with actor and type, we render it dynamically
        if n.actor and n.notif_type:
            if n.notif_type == 'join_request':
                title = t_py('notif_join_request_title', lang).format(username=actor_name, group_name=extra.get('group_name', ''))
                message = t_py('notif_join_request_msg', lang).format(username=actor_name)
            elif n.notif_type == 'join_accepted':
                title = t_py('notif_join_accepted_title', lang).format(group_name=extra.get('group_name', ''))
                message = t_py('notif_join_accepted_msg', lang).format(group_name=extra.get('group_name', ''))
            elif n.notif_type == 'join_rejected':
                title = t_py('notif_join_rejected_title', lang).format(group_name=extra.get('group_name', ''))
                message = t_py('notif_join_rejected_msg', lang).format(group_name=extra.get('group_name', ''))
            elif n.notif_type == 'post_approved':
                if 'group_name' in extra: # Review request
                    title = t_py('notif_post_review_title', lang).format(post_title=extra.get('post_title', ''))
                    message = t_py('notif_post_review_msg', lang).format(username=actor_name, post_title=extra.get('post_title', ''), group_name=extra.get('group_name', ''))
                else: # Real approval
                    title = t_py('notif_post_approved_title', lang).format(post_title=extra.get('post_title', ''))
                    message = t_py('notif_post_approved_msg', lang).format(post_title=extra.get('post_title', ''))
                    if extra.get('comment'):
                        message += f" ({extra['comment']})"
            elif n.notif_type == 'post_rejected':
                title = t_py('notif_post_rejected_title', lang).format(post_title=extra.get('post_title', ''))
                message = t_py('notif_post_rejected_msg', lang).format(post_title=extra.get('post_title', ''), group_name=extra.get('group_name', ''))
                if extra.get('comment'):
                    message += f" ({extra['comment']})"
            elif n.notif_type == 'new_follower':
                title = t_py('notif_follower_title', lang).format(username=actor_name)
                message = t_py('notif_follower_msg', lang).format(username=actor_name)
        # If actor is missing but type is present (shouldn't happen for new ones), 
        # or it's an old-style notification, we keep the fallbacks (n.title/n.message)
        elif n.notif_type == 'post_approved':
            if 'group_name' in extra: # Review request
                title = t_py('notif_post_review_title', lang).format(post_title=extra.get('post_title', ''))
                message = t_py('notif_post_review_msg', lang).format(username=actor_name, post_title=extra.get('post_title', ''), group_name=extra.get('group_name', ''))
            else: # Real approval
                title = t_py('notif_post_approved_title', lang).format(post_title=extra.get('post_title', ''))
                message = t_py('notif_post_approved_msg', lang).format(post_title=extra.get('post_title', ''))
                if extra.get('comment'):
                    message += f" ({extra['comment']})"
        elif n.notif_type == 'post_rejected':
            title = t_py('notif_post_rejected_title', lang).format(post_title=extra.get('post_title', ''))
            message = t_py('notif_post_rejected_msg', lang).format(post_title=extra.get('post_title', ''), group_name=extra.get('group_name', ''))
            if extra.get('comment'):
                message += f" ({extra['comment']})"
        elif n.notif_type == 'new_follower':
            title = t_py('notif_follower_title', lang).format(username=actor_name)
            message = t_py('notif_follower_msg', lang).format(username=actor_name)

        data.append({
            'id': n.id,
            'type': n.notif_type,
            'title': title,
            'message': message,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%b %d, %H:%M'),
        })
    return JsonResponse({
        'status': 'ok', 
        'notifications': data, 
        'unread_count': unread_count,
        'unread_messages_count': unread_msgs_count,
        'last_message': msg_data
    })


@login_required
def api_mark_notifications_read(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=405)


@login_required
def group_leave(request, pk):
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    if membership and membership.role != 'teacher':
        membership.delete()
    return redirect('groups:list')


@login_required
def add_note_to_group(request, pk):
    """Add an existing note (post) to a group, or create a new one linked to the group."""
    from posts.models import Post
    group = get_object_or_404(StudyGroup, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    lang = request.session.get('lang', 'ru')

    if not membership:
        return redirect('groups:detail', pk=pk)

    if request.method == 'POST':
        post_id = request.POST.get('post_id')
        if post_id:
            # Adding existing note
            post = get_object_or_404(Post, pk=post_id, author=request.user, post_type='note')
            post.group = group
            post.save()

            if group.group_type == 'moderated':
                # Submit for review
                PostApproval.objects.get_or_create(
                    post=post, group=group, submitted_by=request.user,
                    defaults={'status': 'pending'}
                )
                owner = group.owner()
                if owner:
                    Notification.objects.create(
                        user=owner,
                        actor=request.user,
                        notif_type='post_approved',
                        extra_data={'post_title': post.title, 'group_name': group.name},
                        link=f'/groups/{group.pk}/',
                    )
        return redirect('groups:detail', pk=pk)

    # GET: show form with user's notes not already in this group
    my_notes = Post.objects.filter(
        author=request.user,
        post_type='note'
    ).exclude(group=group).order_by('-created_at')

    return render(request, 'groups/add_note.html', {
        'group': group,
        'my_notes': my_notes,
    })
@login_required
def api_mark_notification_read_single(request, notif_id):
    if request.method == 'POST':
        notif = get_object_or_404(Notification, id=notif_id, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=405)

@login_required
def api_delete_group_message(request, message_id):
    if request.method == 'POST':
        msg = get_object_or_404(GroupMessage, pk=message_id)
        if msg.sender == request.user:
            msg.delete()
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'error', 'msg': 'Permission denied'}, status=403)
    return JsonResponse({'status': 'error'}, status=400)
