from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json, os, re
from .models import Message, MessageAttachment, MessageReaction
from .forms import MessageForm
from groups.models import StudyGroup, GroupMembership
from django.http import FileResponse, HttpResponse
import mimetypes
import datetime
from django.utils import timezone

User = get_user_model()

def translate_key(request, key):
    lang = request.session.get('lang', 'ru')
    lang_file = os.path.join(settings.BASE_DIR, 'static', 'languages.json')
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(lang, data.get('ru', {})).get(key, key)
    except:
        return key

def get_chat_sidebar_data(user):
    from groups.models import GroupMessage
    users_messaged = User.objects.filter(
        Q(sent_messages__receiver=user) | Q(received_messages__sender=user)
    ).distinct().exclude(pk=user.pk)

    recent_data = []
    for u in users_messaged:
        last_msg = Message.objects.filter(
            Q(sender=user, receiver=u) | Q(sender=u, receiver=user)
        ).order_by('-created_at').first()
        
        file_name = None
        if last_msg and not last_msg.text and last_msg.attachments.exists():
            file_name = os.path.basename(last_msg.attachments.first().file.name)
            
        recent_data.append({'user': u, 'last': last_msg, 'file_name': file_name})

    min_dt = timezone.make_aware(datetime.datetime.min)
    recent_data.sort(key=lambda x: x['last'].created_at if x['last'] else min_dt, reverse=True)

    groups_qs = StudyGroup.objects.filter(memberships__user=user).distinct()
    user_groups = []
    for g in groups_qs:
        last_msg = GroupMessage.objects.filter(group=g).order_by('-created_at').first()
        file_name = None
        if last_msg and not last_msg.text and last_msg.attachments.exists():
            file_name = os.path.basename(last_msg.attachments.first().file.name)
        
        user_groups.append({'group': g, 'last': last_msg, 'file_name': file_name})
    
    # Sort groups by last message as well if needed, or leave as is
    user_groups.sort(key=lambda x: x['last'].created_at if x['last'] else min_dt, reverse=True)

    return recent_data, user_groups


@login_required
def chat_list(request):
    recent_users, user_groups = get_chat_sidebar_data(request.user)
    return render(request, 'chat/messenger.html', {
        'recent_users': recent_users,
        'user_groups': user_groups,
        'active_chat': None,
        'active_group': None
    })


@login_required
def chat_detail(request, username):
    other_user = get_object_or_404(User, username=username)
    recent_users, user_groups = get_chat_sidebar_data(request.user)
    form = MessageForm()
    return render(request, 'chat/messenger.html', {
        'recent_users': recent_users,
        'user_groups': user_groups,
        'active_chat': other_user,
        'active_group': None,
        'form': form
    })


@login_required
def api_messages(request, username):
    other_user = get_object_or_404(User, username=username)

    if request.method == 'GET':
        after_id = int(request.GET.get('after_id', 0))
        messages = Message.objects.filter(
            Q(sender=request.user, receiver=other_user, deleted_by_sender=False) |
            Q(sender=other_user, receiver=request.user, deleted_by_receiver=False)
        )
        if after_id > 0:
            messages = messages.filter(id__gt=after_id)

        messages = messages.order_by('created_at').prefetch_related('attachments', 'reactions')

        # Mark all incoming unread messages as read
        Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

        # Check newly read statuses for the user's unread sent messages
        unread_str = request.GET.get('unread', '')
        newly_read_ids = []
        if unread_str:
            unread_list = [int(x) for x in unread_str.split(',') if x.isdigit()]
            if unread_list:
                newly_read_ids = list(Message.objects.filter(
                    id__in=unread_list, is_read=True
                ).values_list('id', flat=True))

        data = []
        for msg in messages:
            # Build attachments list
            attachments = []
            for att in msg.attachments.all():
                raw_name = os.path.basename(att.file.name)
                clean_name = re.sub(r'^[0-9a-f]{32,}_', '', raw_name)
                attachments.append({
                    'url': att.file.url,
                    'name': clean_name,
                })

            # Group reactions
            reactions = {}
            for rx in msg.reactions.all():
                if rx.emoji not in reactions:
                    reactions[rx.emoji] = []
                reactions[rx.emoji].append(rx.user.username)

            data.append({
                'id': msg.id,
                'text': msg.text,
                'sender': msg.sender.username,
                'sender_avatar': msg.sender.avatar.url if msg.sender.avatar else None,
                'attachments': attachments,
                # Legacy single-attachment fields for forward compatibility
                'attachment_url': attachments[0]['url'] if attachments else None,
                'attachment_name': attachments[0]['name'] if attachments else None,
                'created_at': msg.created_at.strftime('%H:%M, %b %d'),
                'forwarded_from': msg.forwarded_from.sender.username if msg.forwarded_from else None,
                'reply_to_text': msg.reply_to.text[:50] if msg.reply_to and msg.reply_to.text else (
                    translate_key(request, "reply_photo") if msg.reply_to and msg.reply_to.attachments.filter(file__regex=r'\.(jpg|jpeg|png|gif|webp)$').exists() else
                    translate_key(request, "reply_music") if msg.reply_to and msg.reply_to.attachments.filter(file__regex=r'\.(mp3|wav|ogg)$').exists() else
                    translate_key(request, "reply_video") if msg.reply_to and msg.reply_to.attachments.filter(file__regex=r'\.(mp4|webm)$').exists() else
                    translate_key(request, "reply_file") if msg.reply_to and msg.reply_to.attachments.exists() else None
                ) if msg.reply_to else None,
                'reply_to_id': msg.reply_to.id if msg.reply_to else None,
                'reply_to_user': msg.reply_to.sender.username if msg.reply_to else None,
                'reactions': reactions,
                'is_read': msg.is_read,
            })
        return JsonResponse({'status': 'ok', 'messages': data, 'newly_read_ids': newly_read_ids})

    elif request.method == 'POST':
        reply_to_id = None
        if request.content_type == 'application/json':
            body = json.loads(request.body)
            text = body.get('text', '')
            reply_to_id = body.get('reply_to_id')
            if text:
                reply_to_msg = Message.objects.filter(id=reply_to_id).first() if reply_to_id else None
                msg = Message.objects.create(
                    sender=request.user, receiver=other_user,
                    text=text, reply_to=reply_to_msg
                )
                return JsonResponse({'status': 'ok', 'id': msg.id})
        else:
            text = request.POST.get('text', '').strip()
            reply_to_id = request.POST.get('reply_to_id')
            files = request.FILES.getlist('attachment')

            # Require at least text or a file
            if not text and not files:
                return JsonResponse({'status': 'error', 'reason': 'empty'}, status=400)

            reply_to_msg = Message.objects.filter(id=reply_to_id).first() if reply_to_id else None
            msg = Message.objects.create(
                sender=request.user,
                receiver=other_user,
                text=text,
                reply_to=reply_to_msg,
            )
            for f in files:
                MessageAttachment.objects.create(message=msg, file=f)

            return JsonResponse({'status': 'ok', 'id': msg.id})

    return JsonResponse({'status': 'error'}, status=400)


@login_required
@csrf_exempt
def api_bulk_forward(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            msg_ids = body.get('msg_ids', [])
            source_type = body.get('source_type', 'user') # 'user' or 'group'
            target_type = body.get('target_type', 'user') # 'user' or 'group'
            target_id = body.get('target_id')

            if not msg_ids or not target_id:
                return JsonResponse({'status': 'error', 'msg': 'Missing data'}, status=400)

            from groups.models import StudyGroup, GroupMessage, GroupMessageAttachment

            for mid in msg_ids:
                text = ""
                attachments = []
                orig_msg = None
                
                if source_type == 'user':
                    msg = get_object_or_404(Message, pk=mid)
                    text = msg.text
                    attachments = msg.attachments.all()
                    orig_msg = msg
                else:
                    msg = get_object_or_404(GroupMessage, pk=mid)
                    text = msg.text
                    attachments = msg.attachments.all()
                    # We can't easily link forwarded_from across models if GroupMessage doesn't have it,
                    # but Message model has forwarded_from. Let's see if we can at least copy text/files.

                if target_type == 'user':
                    target_user = get_object_or_404(User, username=target_id)
                    new_msg = Message.objects.create(
                        sender=request.user,
                        receiver=target_user,
                        text=text,
                        forwarded_from=orig_msg if source_type == 'user' else None
                    )
                    for att in attachments:
                        MessageAttachment.objects.create(message=new_msg, file=att.file)
                else:
                    target_group = get_object_or_404(StudyGroup, pk=target_id)
                    new_msg = GroupMessage.objects.create(
                        group=target_group,
                        sender=request.user,
                        text=text
                    )
                    for att in attachments:
                        GroupMessageAttachment.objects.create(message=new_msg, file=att.file)

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)


@login_required
@csrf_exempt
def api_add_reaction(request, message_id):
    if request.method == 'POST':
        try:
            msg = get_object_or_404(Message, pk=message_id)
            body = json.loads(request.body)
            emoji = body.get('emoji')
            if not emoji:
                return JsonResponse({'status': 'error'}, status=400)

            # 1. Enforce single reaction limit: remove other emojis by this user
            MessageReaction.objects.filter(message=msg, user=request.user).exclude(emoji=emoji).delete()
            
            # 2. Toggle the requested emoji
            rx, created = MessageReaction.objects.get_or_create(
                message=msg, user=request.user, emoji=emoji
            )
            if not created:
                rx.delete()
            
            # 3. Return updated reaction state for immediate UI refresh
            updated_reactions = {}
            for r in msg.reactions.all():
                if r.emoji not in updated_reactions:
                    updated_reactions[r.emoji] = []
                updated_reactions[r.emoji].append(r.user.username)
                
            return JsonResponse({'status': 'ok', 'reactions': updated_reactions})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)


def serve_media(request, path):
    """
    Custom media server supporting Range requests (needed for seeking in video/audio).
    """
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(full_path):
        return HttpResponse(status=404)

    file_size = os.path.getsize(full_path)
    content_type, _ = mimetypes.guess_type(full_path)
    content_type = content_type or 'application/octet-stream'

    range_header = request.META.get('HTTP_RANGE', '').strip()
    if range_header:
        import re
        match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if match:
            start = int(match.group(1))
            end = match.group(2)
            end = int(end) if end else file_size - 1
            
            if start >= file_size:
                return HttpResponse(status=416)
                
            length = end - start + 1
            with open(full_path, 'rb') as f:
                f.seek(start)
                data = f.read(length)
            
            response = HttpResponse(data, status=206, content_type=content_type)
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = length
            return response

    response = FileResponse(open(full_path, 'rb'), content_type=content_type)
    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = file_size
    return response

@login_required
@csrf_exempt
def api_delete_message(request, message_id):
    if request.method == 'POST':
        msg = get_object_or_404(Message, pk=message_id)
        
        # Determine if it's for everyone or just for me
        for_everyone = request.POST.get('for_everyone') == 'true'
        
        if for_everyone:
            if msg.sender == request.user:
                msg.delete()
                return JsonResponse({'status': 'ok'})
            return JsonResponse({'status': 'error', 'msg': 'Permission denied'}, status=403)
        else:
            # Soft delete for me
            if msg.sender == request.user:
                msg.deleted_by_sender = True
            elif msg.receiver == request.user:
                msg.deleted_by_receiver = True
            msg.save()
            return JsonResponse({'status': 'ok'})
            
    return JsonResponse({'status': 'error'}, status=400)
