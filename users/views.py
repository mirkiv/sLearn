from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserLoginForm, ProfileEditForm
from posts.templatetags.custom_dict import t_py

User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            lang = request.session.get('lang', 'ru')
            messages.success(request, t_py('welcome_msg', lang).format(username=user.username))
            return redirect('users:profile')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                lang = request.session.get('lang', 'ru')
                messages.info(request, t_py('logged_in_msg', lang).format(username=username))
                return redirect('users:profile')
            else:
                lang = request.session.get('lang', 'ru')
                messages.error(request, t_py('invalid_login', lang))
    else:
        form = UserLoginForm()
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    lang = request.session.get('lang', 'ru')
    messages.info(request, t_py('logged_out_msg', lang))
    return redirect('users:login')

@login_required
def profile_view(request):
    return user_detail(request, request.user.username)

def user_detail(request, username):
    profile_user = get_object_or_404(User, username=username)
    
    # Stats and lists
    user_posts = profile_user.posts.filter(visibility='public').order_by('-created_at')
    # If viewing self, show all posts including private/unlisted
    if request.user == profile_user:
        user_posts = profile_user.posts.all().order_by('-created_at')
        
    user_groups = profile_user.memberships.all().select_related('group')
    followers = profile_user.followers.all()
    following = profile_user.following.all()
    
    is_following = False
    if request.user.is_authenticated and request.user != profile_user:
        is_following = request.user.following.filter(pk=profile_user.pk).exists()

    context = {
        'profile_user': profile_user,
        'user_posts': user_posts,
        'user_groups': user_groups,
        'followers': followers,
        'following': following,
        'is_following': is_following,
    }
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash

    lang = request.session.get('lang', 'ru')

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            form = ProfileEditForm(request.POST, request.FILES, instance=request.user, lang=lang)
            if form.is_valid():
                form.save()
                messages.success(request, t_py('profile_updated_msg', lang))
                return redirect('users:edit_profile')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, t_py('password_updated_msg', lang))
                return redirect('users:edit_profile')
            
        # If one form is post, other should be empty
        if 'update_profile' not in request.POST:
            form = ProfileEditForm(instance=request.user, lang=lang)
        if 'change_password' not in request.POST:
            password_form = PasswordChangeForm(request.user)
    else:
        form = ProfileEditForm(instance=request.user, lang=lang)
        password_form = PasswordChangeForm(request.user)

    password_form.fields['old_password'].label = t_py('old_password', lang)
    password_form.fields['new_password1'].label = t_py('new_password', lang)
    password_form.fields['new_password2'].label = t_py('confirm_password', lang)
        
    return render(request, 'users/edit_profile.html', {
        'form': form,
        'password_form': password_form
    })

def search_users(request):
    from posts.models import Post
    from groups.models import StudyGroup
    
    query = request.GET.get('q', '').strip()
    
    # Selected tags (users, posts, groups). If empty, assume all are active for basic search
    tags = request.GET.getlist('tags')
    if not tags and 'tags' in request.GET:
        # It means tags was present but empty, but let's parse from comma separated if JS sends it that way
        tags_str = request.GET.get('tags', '')
        if tags_str:
            tags = tags_str.split(',')
    
    # If no tags selected, we can default to all or none. Let's default to all if no specific advanced search is done.
    if not tags:
        tags = ['users', 'posts', 'groups']

    # Advanced filters
    u_username = request.GET.get('u_username', '').strip()
    p_type = request.GET.get('p_type', '').strip()
    p_tags = request.GET.get('p_tags', '').strip()
    g_user = request.GET.get('g_user', '').strip()
    
    user_results = []
    post_results = []
    group_results = []
    
    # We search if there's a main query OR any advanced filter OR tags were explicitly provided
    # If no q or filters, but tags is provided and differs from "all", we should still trigger search
    # But wait, line 130 defaults tags to all if empty. 
    # Let's just always search if q or any field is set, or if q is empty but tags is not all.
    has_filters = any([query, u_username, p_type, p_tags, g_user])
    
    if has_filters:
        # --- USERS ---
        if 'users' in tags:
            qs = User.objects.all()
            if query:
                qs = qs.filter(username__icontains=query)
            if u_username:
                qs = qs.filter(username__icontains=u_username)
            if request.user.is_authenticated:
                qs = qs.exclude(pk=request.user.pk)
            user_results = qs.distinct()[:20]
            
        # --- POSTS ---
        if 'posts' in tags:
            qs = Post.objects.filter(visibility='public')
            if query:
                qs = qs.filter(title__icontains=query)
            if p_type:
                qs = qs.filter(post_type=p_type)
            if p_tags:
                # Use ManyToMany relation for hashtags
                for tag_name in p_tags.replace(',', ' ').split():
                    # remove # if user typed it
                    clean_tag = tag_name.replace('#', '')
                    qs = qs.filter(hashtags__name__icontains=clean_tag)
            post_results = qs.select_related('author').order_by('-created_at').distinct()[:20]
            
        # --- GROUPS ---
        if 'groups' in tags:
            qs = StudyGroup.objects.all()
            if query:
                qs = qs.filter(name__icontains=query)
            if g_user:
                qs = qs.filter(memberships__user__username__icontains=g_user)
            group_results = qs.distinct()[:20]
    
    return render(request, 'users/search.html', {
        'user_results': user_results,
        'post_results': post_results,
        'group_results': group_results,
        'query': query,
        'tags': tags,
        'u_username': u_username,
        'p_type': p_type,
        'p_tags': p_tags,
        'g_user': g_user,
    })

@login_required
def toggle_follow(request, username):
    from groups.models import Notification
    target_user = get_object_or_404(User, username=username)
    if target_user != request.user:
        if request.user.following.filter(username=username).exists():
            request.user.following.remove(target_user)
            lang = request.session.get('lang', 'ru')
            messages.success(request, t_py('unfollowed_msg', lang).format(username=username))
        else:
            request.user.following.add(target_user)
            lang = request.session.get('lang', 'ru')
            messages.success(request, t_py('followed_msg', lang).format(username=username))
            # Add notification for the target user
            Notification.objects.create(
                user=target_user,
                actor=request.user,
                notif_type='new_follower',
                link=f'/users/{request.user.username}/'
            )
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def saved_posts_view(request):
    posts = request.user.saved_posts.all().order_by('-created_at')
    return render(request, 'users/saved_posts.html', {'posts': posts})

def set_language(request, base_lang):
    request.session['lang'] = base_lang
    # Ensure session is saved even for anonymous users
    request.session.modified = True
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('home')
