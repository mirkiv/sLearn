from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Post, NoteChapter, Hashtag, Attachment
from .forms import PostForm, NoteChapterForm
import os
from .templatetags.custom_dict import t_py

@login_required
def post_list(request):
    user_groups = request.user.memberships.values_list('group_id', flat=True)
    following_users = request.user.following.all()
    
    posts = Post.objects.filter(
        Q(author=request.user) | 
        Q(visibility='public') | 
        Q(visibility='friends', author__in=following_users) |
        Q(group_id__in=user_groups)
    ).distinct().order_by('-created_at')
    
    return render(request, 'posts/list.html', {'posts': posts})

@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    following_users = request.user.following.all()
    
    lang = request.session.get('lang', 'ru')
    if post.visibility == 'private' and post.author != request.user:
        messages.error(request, t_py('error_no_permission_post', lang))
        return redirect('posts:list')
    if post.visibility == 'friends' and post.author != request.user and post.author not in following_users and request.user not in post.author.following.all():
        messages.error(request, t_py('error_friends_only', lang))
        return redirect('posts:list')
        
    chapters = post.chapters.all()
    attachments = post.attachments.all()
    chapter_form = NoteChapterForm()
    
    return render(request, 'posts/detail.html', {
        'post': post,
        'chapters': chapters,
        'attachments': attachments,
        'chapter_form': chapter_form
    })

@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            
            hashtags_str = form.cleaned_data.get('hashtags_input', '')
            tags = [t.strip().replace('#', '') for t in hashtags_str.split(' ') if t.strip()]
            for tag_name in tags:
                if tag_name:
                    tag_obj, created = Hashtag.objects.get_or_create(name=tag_name)
                    post.hashtags.add(tag_obj)
            
            lang = request.session.get('lang', 'ru')
            if post.post_type == 'note':
                messages.success(request, t_py('note_created_msg', lang))
            else:
                p_type = post.get_post_type_display()
                messages.success(request, t_py('post_created_msg', lang).format(type=p_type))
            return redirect('posts:detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'posts/create.html', {'form': form})

@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    lang = request.session.get('lang', 'ru')
    if post.author != request.user:
        messages.error(request, t_py('error_edit_others_post', lang))
        return redirect('posts:detail', pk=post.pk)
        
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save()
            # Update hashtags
            post.hashtags.clear()
            hashtags_str = form.cleaned_data.get('hashtags_input', '')
            tags = [t.strip().replace('#', '') for t in hashtags_str.split(' ') if t.strip()]
            for tag_name in tags:
                if tag_name:
                    tag_obj, created = Hashtag.objects.get_or_create(name=tag_name)
                    post.hashtags.add(tag_obj)
            
            lang = request.session.get('lang', 'ru')
            messages.success(request, t_py('post_updated_msg', lang))
            return redirect('posts:detail', pk=post.pk)
    else:
        # Pre-fill hashtags logic
        existing_tags = " ".join([f"#{tag.name}" for tag in post.hashtags.all()])
        initial_data = {'hashtags_input': existing_tags}
        form = PostForm(instance=post, initial=initial_data)
        
    return render(request, 'posts/edit.html', {'form': form, 'post': post})

def feed_view(request):
    posts = Post.objects.filter(visibility='public').order_by('-created_at')[:20]
    
    # If authenticated, prioritize posts containing hashtags the user has used
    if request.user.is_authenticated:
        my_tags = Hashtag.objects.filter(posts__author=request.user).distinct()
        if my_tags.exists():
            posts = Post.objects.filter(
                Q(visibility='public') | 
                Q(visibility='friends', author__in=request.user.following.all())
            ).filter(hashtags__in=my_tags).distinct().order_by('-created_at')[:20]
            
            # If not enough recommended posts, just fallback to recent
            if posts.count() < 3:
                posts = Post.objects.filter(
                    Q(visibility='public') | 
                    Q(visibility='friends', author__in=request.user.following.all())
                ).distinct().order_by('-created_at')[:20]
                
    return render(request, 'home.html', {'recent_posts': posts})

@login_required
def add_chapter(request, pk):
    post = get_object_or_404(Post, pk=pk)
    lang = request.session.get('lang', 'ru')
    if post.author != request.user:
        messages.error(request, t_py('error_only_author_chapters', lang))
        return redirect('posts:detail', pk=post.pk)
        
    if request.method == 'POST':
        form = NoteChapterForm(request.POST, request.FILES)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.post = post
            chapter.order = post.chapters.count() + 1
            chapter.save()
            lang = request.session.get('lang', 'ru')
            messages.success(request, t_py('chapter_added_msg', lang))
    return redirect('posts:detail', pk=post.pk)

@login_required
@require_POST
def upload_file(request):
    """API endpoint: upload a file, return JSON {url, name, is_image}."""
    f = request.FILES.get('file')
    lang = request.session.get('lang', 'ru')
    if not f:
        return JsonResponse({'error': t_py('error_no_file', lang)}, status=400)

    # Limit size: 10 MB
    if f.size > 10 * 1024 * 1024:
        return JsonResponse({'error': t_py('error_file_too_large_editor', lang)}, status=400)

    # Allowed extensions
    ALLOWED = {
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'md', 'zip', 'mp4', 'mp3',
    }
    ext = os.path.splitext(f.name)[1].lstrip('.').lower()
    if ext not in ALLOWED:
        return JsonResponse({'error': t_py('error_file_type_not_allowed', lang).format(ext=ext)}, status=400)

    IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}

    # Save as an Attachment linked to a placeholder post=None style
    # We store it temporarily under media/post_attachments/
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import uuid
    unique_name = f"{uuid.uuid4().hex}_{f.name}"
    path = default_storage.save(f'editor_uploads/{unique_name}', ContentFile(f.read()))
    url = default_storage.url(path)

    return JsonResponse({
        'url': url,
        'name': f.name,
        'is_image': ext in IMAGE_EXTS,
    })

@login_required
def toggle_save(request, pk):
    post = get_object_or_404(Post, pk=pk)
    lang = request.session.get('lang', 'ru')
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.user.saved_posts.filter(pk=post.pk).exists():
        request.user.saved_posts.remove(post)
        saved = False
        msg = t_py('post_unsaved_msg', lang)
    else:
        request.user.saved_posts.add(post)
        saved = True
        msg = t_py('post_saved_msg', lang)
    
    if is_ajax:
        return JsonResponse({'saved': saved, 'message': msg})
    
    messages.success(request, msg)
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('posts:detail', pk=post.pk)

@login_required
@require_POST
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    lang = request.session.get('lang', 'ru')
    if post.author != request.user:
        messages.error(request, t_py('error_delete_others_post', lang))
        return redirect('posts:detail', pk=post.pk)
    
    post.delete()
    messages.success(request, t_py('post_deleted_msg', lang))
    return redirect('posts:list')
