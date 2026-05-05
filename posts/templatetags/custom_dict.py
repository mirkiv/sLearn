from django import template
import json
import os
from django.conf import settings

register = template.Library()

# Load language file
LANG_FILE = os.path.join(settings.BASE_DIR, 'static', 'languages.json')

def load_translations():
    try:
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'ru': {}, 'en': {}}

TRANSLATIONS = load_translations()

def t_py(key, lang='ru', **kwargs):
    global TRANSLATIONS
    SUPPORTED = {'en', 'ru', 'uz', 'fr', 'de'}
    if lang not in SUPPORTED:
        lang = 'ru'
    
    # Always reload translations to ensure new keys are picked up without server restart
    TRANSLATIONS = load_translations()
        
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS.get('ru', {}))
    # Fallback to RU then to key
    val = lang_dict.get(key, TRANSLATIONS.get('ru', {}).get(key, key))
    
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val

@register.simple_tag(takes_context=True)
def t(context, key, **kwargs):
    request = context.get('request')
    # Allow overriding lang via kwargs, otherwise use session lang
    lang = kwargs.pop('lang', getattr(request, 'session', {}).get('lang', 'ru'))
    return t_py(key, lang, **kwargs)
