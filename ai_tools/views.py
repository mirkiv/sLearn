import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from posts.models import Post
from posts.templatetags.custom_dict import t_py
from .models import AIProviderSettings, AIHistory
from google import genai
import re

PROVIDERS = {
    'gemini': {
        'name': 'Gemini',
        'url': 'https://aistudio.google.com/app/apikey',
        'api_base': '',
        'model': 'gemini-2.5-flash',
        'logo': '<svg width="24" height="24" viewBox="0 0 65 65" fill="currentColor"><path d="M32.447 0c.68 0 1.273.465 1.439 1.125a38.904 38.904 0 001.999 5.905c2.152 5 5.105 9.376 8.854 13.125 3.751 3.75 8.126 6.703 13.125 8.855a38.98 38.98 0 005.906 1.999c.66.166 1.124.758 1.124 1.438 0 .68-.464 1.273-1.125 1.439a38.902 38.902 0 00-5.905 1.999c-5 2.152-9.375 5.105-13.125 8.854-3.749 3.751-6.702 8.126-8.854 13.125a38.973 38.973 0 00-2 5.906 1.485 1.485 0 01-1.438 1.124c-.68 0-1.272-.464-1.438-1.125a38.913 38.913 0 00-2-5.905c-2.151-5-5.103-9.375-8.854-13.125-3.75-3.749-8.125-6.702-13.125-8.854a38.973 38.973 0 00-5.905-2A1.485 1.485 0 010 32.448c0-.68.465-1.272 1.125-1.438a38.903 38.903 0 005.905-2c5-2.151 9.376-5.104 13.125-8.854 3.75-3.749 6.703-8.125 8.855-13.125a38.972 38.972 0 001.999-5.905A1.485 1.485 0 0132.447 0z"/></svg>',
    },
    'deepseek': {
        'name': 'DeepSeek',
        'url': 'https://platform.deepseek.com/api_keys',
        'api_base': 'https://api.deepseek.com/chat/completions',
        'model': 'deepseek-chat',
        'logo': '<svg width="24" height="24" viewBox="0 0 512 509.64" fill="currentColor"><path fill-rule="nonzero" d="M440.898 139.167c-4.001-1.961-5.723 1.776-8.062 3.673-.801.612-1.479 1.407-2.154 2.141-5.848 6.246-12.681 10.349-21.607 9.859-13.048-.734-24.192 3.368-34.04 13.348-2.093-12.307-9.048-19.658-19.635-24.37-5.54-2.449-11.141-4.9-15.02-10.227-2.708-3.795-3.447-8.021-4.801-12.185-.861-2.509-1.725-5.082-4.618-5.512-3.139-.49-4.372 2.142-5.601 4.349-4.925 9.002-6.833 18.921-6.647 28.962.432 22.597 9.972 40.597 28.932 53.397 2.154 1.47 2.707 2.939 2.032 5.082-1.293 4.41-2.832 8.695-4.186 13.105-.862 2.817-2.157 3.429-5.172 2.205-10.402-4.346-19.391-10.778-27.332-18.553-13.481-13.044-25.668-27.434-40.873-38.702a177.614 177.614 0 00-10.834-7.409c-15.512-15.063 2.032-27.434 6.094-28.902 4.247-1.532 1.478-6.797-12.251-6.736-13.727.061-26.285 4.653-42.288 10.777-2.34.92-4.801 1.593-7.326 2.142-14.527-2.756-29.608-3.368-45.367-1.593-29.671 3.305-53.368 17.329-70.788 41.272-20.928 28.785-25.854 61.482-19.821 95.59 6.34 35.943 24.683 65.704 52.876 88.974 29.239 24.123 62.911 35.943 101.32 33.677 23.329-1.346 49.307-4.468 78.607-29.27 7.387 3.673 15.142 5.144 28.008 6.246 9.911.92 19.452-.49 26.839-2.019 11.573-2.449 10.773-13.166 6.586-15.124-33.915-15.797-26.47-9.368-33.24-14.573 17.235-20.39 43.213-41.577 53.369-110.222.8-5.448.121-8.877 0-13.287-.061-2.692.553-3.734 3.632-4.041 8.494-.981 16.742-3.305 24.314-7.471 21.975-12.002 30.84-31.719 32.933-55.355.307-3.612-.061-7.348-3.879-9.245v-.003zM249.4 351.89c-32.872-25.838-48.814-34.352-55.4-33.984-6.155.368-5.048 7.41-3.694 12.002 1.415 4.532 3.264 7.654 5.848 11.634 1.785 2.634 3.017 6.551-1.784 9.493-10.587 6.55-28.993-2.205-29.856-2.635-21.421-12.614-39.334-29.269-51.954-52.047-12.187-21.924-19.267-45.435-20.435-70.542-.308-6.061 1.478-8.207 7.509-9.307 7.94-1.471 16.127-1.778 24.068-.615 33.547 4.9 62.108 19.902 86.054 43.66 13.666 13.531 24.007 29.699 34.658 45.496 11.326 16.778 23.514 32.761 39.026 45.865 5.479 4.592 9.848 8.083 14.035 10.656-12.62 1.407-33.673 1.714-48.075-9.676zm15.899-102.519c.521-2.111 2.421-3.658 4.722-3.658a4.74 4.74 0 011.661.305c.678.246 1.293.614 1.786 1.163.861.859 1.354 2.083 1.354 3.368 0 2.695-2.154 4.837-4.862 4.837a4.748 4.748 0 01-4.738-4.034 5.01 5.01 0 01.077-1.981zm47.208 26.915c-2.606.996-5.2 1.778-7.707 1.88-4.679.244-9.787-1.654-12.556-3.981-4.308-3.612-7.386-5.631-8.679-11.941-.554-2.695-.247-6.858.246-9.246 1.108-5.144-.124-8.451-3.754-11.451-2.954-2.449-6.711-3.122-10.834-3.122-1.539 0-2.954-.673-4.001-1.224-1.724-.856-3.139-3-1.785-5.634.432-.856 2.525-2.939 3.018-3.305 5.6-3.185 12.065-2.144 18.034.244 5.54 2.266 9.727 6.429 15.759 12.307 6.155 7.102 7.263 9.063 10.773 14.39 2.771 4.163 5.294 8.451 7.018 13.348.877 2.561.071 4.74-2.341 6.277-.981.625-2.109 1.044-3.191 1.458z"/></svg>',
    },
    'chatgpt': {
        'name': 'ChatGPT',
        'url': 'https://openrouter.ai/api/v1',
        'api_base': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-4o-mini',
        'logo': '<svg width="24" height="24" viewBox="0 0 512 512" fill="currentColor"><path d="M412.037 221.764a90.834 90.834 0 004.648-28.67 90.79 90.79 0 00-12.443-45.87c-16.37-28.496-46.738-46.089-79.605-46.089-6.466 0-12.943.683-19.264 2.04a90.765 90.765 0 00-67.881-30.515h-.576c-.059.002-.149.002-.216.002-39.807 0-75.108 25.686-87.346 63.554-25.626 5.239-47.748 21.31-60.682 44.03a91.873 91.873 0 00-12.407 46.077 91.833 91.833 0 0023.694 61.553 90.802 90.802 0 00-4.649 28.67 90.804 90.804 0 0012.442 45.87c16.369 28.504 46.74 46.087 79.61 46.087a91.81 91.81 0 0019.253-2.04 90.783 90.783 0 0067.887 30.516h.576l.234-.001c39.829 0 75.119-25.686 87.357-63.588 25.626-5.242 47.748-21.312 60.682-44.033a91.718 91.718 0 0012.383-46.035 91.83 91.83 0 00-23.693-61.553l-.004-.005zM275.102 413.161h-.094a68.146 68.146 0 01-43.611-15.8 56.936 56.936 0 002.155-1.221l72.54-41.901a11.799 11.799 0 005.962-10.251V241.651l30.661 17.704c.326.163.55.479.596.84v84.693c-.042 37.653-30.554 68.198-68.21 68.273h.001zm-146.689-62.649a68.128 68.128 0 01-9.152-34.085c0-3.904.341-7.817 1.005-11.663.539.323 1.48.897 2.155 1.285l72.54 41.901a11.832 11.832 0 0011.918-.002l88.563-51.137v35.408a1.1 1.1 0 01-.438.94l-73.33 42.339a68.43 68.43 0 01-34.11 9.12 68.359 68.359 0 01-59.15-34.11l-.001.004zm-19.083-158.36a68.044 68.044 0 0135.538-29.934c0 .625-.036 1.731-.036 2.5v83.801l-.001.07a11.79 11.79 0 005.954 10.242l88.564 51.13-30.661 17.704a1.096 1.096 0 01-1.034.093l-73.337-42.375a68.36 68.36 0 01-34.095-59.143 68.412 68.412 0 019.112-34.085l-.004-.003zm251.907 58.621l-88.563-51.137 30.661-17.697a1.097 1.097 0 011.034-.094l73.337 42.339c21.109 12.195 34.132 34.746 34.132 59.132 0 28.604-17.849 54.199-44.686 64.078v-86.308c.004-.032.004-.065.004-.096 0-4.219-2.261-8.119-5.919-10.217zm30.518-45.93c-.539-.331-1.48-.898-2.155-1.286l-72.54-41.901a11.842 11.842 0 00-5.958-1.611c-2.092 0-4.15.558-5.957 1.611l-88.564 51.137v-35.408l-.001-.061a1.1 1.1 0 01.44-.88l73.33-42.303a68.301 68.301 0 0134.108-9.129c37.704 0 68.281 30.577 68.281 68.281a68.69 68.69 0 01-.984 11.545v.005zm-191.843 63.109l-30.668-17.704a1.09 1.09 0 01-.596-.84v-84.692c.016-37.685 30.593-68.236 68.281-68.236a68.332 68.332 0 0143.689 15.804 63.09 63.09 0 00-2.155 1.222l-72.54 41.9a11.794 11.794 0 00-5.961 10.248v.068l-.05 102.23zm16.655-35.91l39.445-22.782 39.444 22.767v45.55l-39.444 22.767-39.445-22.767v-45.535z"/></svg>',
    }
}

VOLUME_PROMPTS = {
    'original': {'label': 'Исходный размер', 'desc': 'Генерация будет стараться придерживаться исходного размера выбранных конспектов', 'prompt': 'Постарайся придерживаться исходного размера текста.'},
    'supershort': {'label': 'Супер краткий', 'desc': 'Максимально важная выжимка из конспектов без воды', 'prompt': 'Сделай максимально важную выжимку из конспектов без воды, очень коротко.'},
    'short': {'label': 'Кратко', 'desc': 'Только суть без воды', 'prompt': 'Напиши только суть без воды, кратко.'},
    'medium': {'label': 'Средний', 'desc': 'Баланс между размером и сутью', 'prompt': 'Соблюдай баланс между размером и сутью, не слишком коротко, но и не затянуто.'},
    'large': {'label': 'Большой', 'desc': 'Максимально подробный конспект не упуская деталей', 'prompt': 'Сделай максимально подробный конспект, не упуская деталей.'}
}

def translate_error(error_code_or_msg):
    msg = str(error_code_or_msg).lower()
    if '401' in msg or 'unauthorized' in msg or 'invalid api key' in msg or 'authentication' in msg:
        return 'Неверный API ключ. Пожалуйста, проверьте правильность введенного ключа.'
    elif '404' in msg or 'not found' in msg:
        return 'Модель или эндпоинт не найдены (Ошибка 404).'
    elif '429' in msg or 'quota' in msg or 'rate limit' in msg:
        return 'Превышен лимит запросов. Попробуйте позже или проверьте баланс API.'
    elif '400' in msg or 'bad request' in msg:
        return 'Некорректный запрос (Ошибка 400). Возможно, текст слишком длинный.'
    return f'Произошла ошибка при обращении к ИИ: {error_code_or_msg}'

DEFAULT_PROMPT = """Объедини следующие конспекты в один понятный, четкий, структурированный конспект. Сделай его легко читаемым, выдели главное, вырежи дублирующиеся отрывки текста.
Сохрани формат записи медиа и LaTeX формул если они содержатся в тексте.
Используй формат Markdown для самого конспекта.
СВОЙ ОТВЕТ СТРОГО ОБЕРНИ В ТЕГИ:
<comment>Ваши вступительные и заключительные комментарии, размышления о проделанной работе (не входят в сам конспект)</comment>
<note>Сам структурированный конспект в формате Markdown без лишних слов</note>"""
def get_available_notes(user):
    return user.saved_posts.filter(post_type='note')

@login_required
def ai_dashboard(request):
    last_provider = request.session.get('last_ai_provider', 'gemini')
    if last_provider not in PROVIDERS:
        last_provider = 'gemini'
    return redirect('ai_tools:provider_view', provider=last_provider)

@login_required
def ai_provider_view(request, provider):
    if provider not in PROVIDERS:
        return redirect('ai_tools:combine')
        
    request.session['last_ai_provider'] = provider
        
    ai_settings, _ = AIProviderSettings.objects.get_or_create(user=request.user, provider=provider)
    
    if not ai_settings.api_key:
        return render(request, 'ai_tools/setup.html', {
            'provider': provider,
            'provider_info': PROVIDERS[provider],
            'providers': PROVIDERS,
        })
        
    saved_notes = get_available_notes(request.user)
    history_qs = AIHistory.objects.filter(user=request.user, provider=provider).order_by('-created_at')
    
    parsed_history = []
    for h in history_qs:
        parsed_history.append({
            'id': h.id,
            'created_at': h.created_at,
            'source_notes': h.source_notes.all(),
            'comment': h.comment,
            'note': h.note
        })
    
    return render(request, 'ai_tools/dashboard.html', {
        'provider': provider,
        'provider_info': PROVIDERS[provider],
        'providers': PROVIDERS,
        'ai_settings': ai_settings,
        'saved_notes': saved_notes,
        'history': parsed_history,
        'volumes': VOLUME_PROMPTS,
    })

@login_required
def validate_api_key(request, provider):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})
        
    if provider not in PROVIDERS:
        return JsonResponse({'status': 'error', 'message': 'Invalid provider'})
        
    data = json.loads(request.body)
    api_key = data.get('api_key', '').strip()
    
    if not api_key:
        return JsonResponse({'status': 'error', 'message': 'API key is required'})
        
    try:
        if provider == 'gemini':
            client = genai.Client(api_key=api_key)
            client.models.generate_content(model=PROVIDERS[provider]['model'], contents="test")
        else:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': PROVIDERS[provider]['model'],
                'messages': [{'role': 'user', 'content': 'test'}],
                'max_tokens': 5
            }
            resp = requests.post(PROVIDERS[provider]['api_base'], headers=headers, json=payload)
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
                
        ai_settings, _ = AIProviderSettings.objects.get_or_create(user=request.user, provider=provider)
        ai_settings.api_key = api_key
        ai_settings.save()
        
        return JsonResponse({'status': 'success', 'message': 'Успешно подключен AI!'})
        
    except Exception as e:
        error_msg = translate_error(e)
        return JsonResponse({'status': 'error', 'message': error_msg})

@login_required
def provider_settings(request, provider):
    if provider not in PROVIDERS:
        return redirect('ai_tools:combine')
        
    ai_settings, _ = AIProviderSettings.objects.get_or_create(user=request.user, provider=provider)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reset':
            ai_settings.api_key = ''
            ai_settings.custom_prompt = ''
            ai_settings.language = 'default'
            ai_settings.ai_model = ''
            ai_settings.save()
            messages.success(request, "Настройки успешно сброшены.")
            return redirect('ai_tools:provider_view', provider=provider)
            
        ai_settings.api_key = request.POST.get('api_key', '').strip() or ai_settings.api_key
        ai_settings.custom_prompt = request.POST.get('custom_prompt', '').strip()
        ai_settings.language = request.POST.get('language', 'default')
        if request.POST.get('ai_model'):
            ai_settings.ai_model = request.POST.get('ai_model')
        ai_settings.save()

        
        if request.POST.get('apply_all_lang') == '1':
            for p in PROVIDERS:
                if p != provider:
                    other_settings, _ = AIProviderSettings.objects.get_or_create(user=request.user, provider=p)
                    other_settings.language = ai_settings.language
                    other_settings.save()
                    
        if request.POST.get('apply_all_prompt') == '1':
            for p in PROVIDERS:
                if p != provider:
                    other_settings, _ = AIProviderSettings.objects.get_or_create(user=request.user, provider=p)
                    other_settings.custom_prompt = ai_settings.custom_prompt
                    other_settings.save()
                    
        messages.success(request, "Настройки успешно сохранены.")
        return redirect('ai_tools:provider_view', provider=provider)
        
    import requests
    available_models = []
    if ai_settings.api_key:
        try:
            if provider == 'gemini':
                client = genai.Client(api_key=ai_settings.api_key)
                models = client.models.list_models()
                for m in models:
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append({'id': m.name.replace('models/', ''), 'name': m.display_name or m.name.replace('models/', '')})
            else:
                url = 'https://api.openai.com/v1/models' if provider == 'chatgpt' else 'https://api.deepseek.com/models'
                headers = {'Authorization': f'Bearer {ai_settings.api_key}'}
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get('data', []):
                        available_models.append({'id': m['id'], 'name': m['id']})
        except Exception as e:
            print("Failed to fetch models:", e)

    return render(request, 'ai_tools/settings.html', {
        'provider': provider,
        'provider_info': PROVIDERS[provider],
        'providers': PROVIDERS,
        'ai_settings': ai_settings,
        'default_prompt': DEFAULT_PROMPT,
        'available_models': available_models,
    })

@login_required
def combine_notes_action(request, provider):
    if provider not in PROVIDERS:
        return redirect('ai_tools:combine')
        
    if request.method == 'POST':
        ai_settings, _ = AIProviderSettings.objects.get_or_create(user=request.user, provider=provider)
        if not ai_settings.api_key:
            return redirect('ai_tools:provider_view', provider=provider)
            
        note_ids = request.POST.getlist('notes')
        volume = request.POST.get('volume', 'medium')
        
        if not (2 <= len(note_ids) <= 5):
            messages.error(request, "Выберите от 2 до 5 конспектов.")
            return redirect('ai_tools:provider_view', provider=provider)
            
        selected_notes = get_available_notes(request.user).filter(id__in=note_ids)
        
        all_text = []
        for note in selected_notes:
            all_text.append(f"--- Конспект: {note.title} ---")
            hashtags = ", ".join([h.name for h in note.hashtags.all()])
            if hashtags:
                all_text.append(f"Хэштеги: {hashtags}")
            if note.content:
                all_text.append(f"Содержание:\n{note.content}")
            for chapter in note.chapters.all():
                all_text.append(f"Глава: {chapter.title}\n{chapter.text_content}")
                
        compiled_text = "\n\n".join(all_text)
        
        volume_instruction = VOLUME_PROMPTS.get(volume, VOLUME_PROMPTS['medium'])['prompt']
        base_prompt = ai_settings.custom_prompt
        if not base_prompt:
            base_prompt = DEFAULT_PROMPT
            
        lang_str = ""
        effective_lang = ai_settings.language
        if effective_lang == 'default':
            effective_lang = request.session.get('lang', 'ru')
            
        if effective_lang == 'ru':
            lang_str = "Отвечай на русском языке."
        elif effective_lang == 'en':
            lang_str = "Answer in English."
        elif effective_lang == 'uz':
            lang_str = "Javobni o'zbek tilida bering."
        elif effective_lang == 'fr':
            lang_str = "Répondez en français."
        elif effective_lang == 'de':
            lang_str = "Antworten Sie auf Deutsch."
            
        prompt = f"{base_prompt}\n\n{volume_instruction}\n{lang_str}\n\n{compiled_text}"
        
        try:
            combined_result = ""
            current_model = ai_settings.ai_model if ai_settings.ai_model else PROVIDERS[provider]['model']
            
            if provider == 'gemini':
                client = genai.Client(api_key=ai_settings.api_key)
                response = client.models.generate_content(
                    model=current_model, 
                    contents=prompt
                )
                combined_result = response.text
            else:
                headers = {
                    'Authorization': f'Bearer {ai_settings.api_key}',
                    'Content-Type': 'application/json'
                }
                payload = {
                    'model': current_model,
                    'messages': [{'role': 'user', 'content': prompt}],
                }
                resp = requests.post(PROVIDERS[provider]['api_base'], headers=headers, json=payload)
                if resp.status_code != 200:
                    raise Exception(f"HTTP {resp.status_code}: {resp.text}")
                data = resp.json()
                combined_result = data['choices'][0]['message']['content']
                
            history = AIHistory.objects.create(
                user=request.user,
                provider=provider,
                result_text=combined_result
            )
            history.source_notes.set(selected_notes)
            
            return redirect('ai_tools:provider_view', provider=provider)
            
        except Exception as e:
            messages.error(request, translate_error(str(e)))
    return redirect('ai_tools:provider_view', provider=provider)

@login_required
def save_as_note(request):
    if request.method == 'POST':
        history_id = request.POST.get('history_id')
        try:
            h = AIHistory.objects.get(id=history_id, user=request.user)
            
            note_text = h.note
                
            post = Post.objects.create(
                author=request.user,
                post_type='note',
                title="Сгенерированный конспект",
                content=note_text,
                visibility='private'
            )
            for source in h.source_notes.all():
                for tag in source.hashtags.all():
                    post.hashtags.add(tag)
                    
            messages.success(request, "Конспект успешно сохранен. Теперь вы можете его отредактировать.")
            return redirect('posts:edit', pk=post.pk)
        except AIHistory.DoesNotExist:
            messages.error(request, "Запись не найдена.")
            
    last_provider = request.session.get('last_ai_provider', 'gemini')
    return redirect('ai_tools:provider_view', provider=last_provider)
