from django import template
from django.utils.safestring import mark_safe
import markdown, re

register = template.Library()

# File-type emoji icons (matches JS FILE_ICONS map)
FILE_ICONS = {
    'pdf': '📕', 'doc': '📝', 'docx': '📝',
    'xls': '📊', 'xlsx': '📊', 'csv': '📊', 'ppt': '📊', 'pptx': '📊',
    'zip': '🗜', 'rar': '🗜',
    'txt': '📄', 'md': '📄',
    'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨',
    'mp4': '🎬', 'mp3': '🎵', 'mov': '🎬', 'avi': '🎬',
    'png': '🖼', 'jpg': '🖼', 'jpeg': '🖼', 'gif': '🖼', 'svg': '🖼', 'webp': '🖼',
}

IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}


def _file_icon(ext):
    return FILE_ICONS.get(ext.lower(), '📎')


def _build_file_block(url, name=None):
    """Return an HTML file-attachment card for non-image files."""
    url = url.strip()
    if not name:
        # Strip leading uuid hex prefix added by upload_file view
        raw = url.split('/')[-1]
        name = re.sub(r'^[0-9a-f]{32,}_', '', raw)
    else:
        name = name.strip()
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    icon = _file_icon(ext)
    badge = f'<span class="fab-badge">.{ext}</span>' if ext else ''
    return (
        f'<a href="{url}" class="fab" download="{name}" target="_blank">'
        f'<span class="fab-ico">{icon}</span>'
        f'{badge}'
        f'<span class="fab-name">{name}</span>'
        f'<span class="fab-dl">↓</span>'
        f'</a>'
    )


def _media_replace(url, alt=None):
    url = url.strip()
    ext = url.rsplit('.', 1)[-1].split('?')[0].lower()
    if ext in IMAGE_EXTS:
        return f'<img src="{url}" alt="{alt or ""}" style="max-width:100%;border-radius:8px;margin:8px 0;display:block;" onerror="this.style.display=\'none\'">'
    return _build_file_block(url, alt)


@register.filter(name='markdown')
def markdown_format(text):
    if not text:
        return ''

    # Preserve LaTeX by stashing before any other processing
    placeholders = {}
    counter = [0]

    def stash(m):
        key = f'LATEXPH{counter[0]}X'
        placeholders[key] = m.group(0)
        counter[0] += 1
        return key

    text = re.sub(r'\$\$[\s\S]+?\$\$', stash, text)
    text = re.sub(r'\$[^\$\n]+?\$', stash, text)

    # ![alt](url) — standard Markdown image/file
    text = re.sub(
        r'!\[(.*?)\]\((.*?)\)',
        lambda m: _media_replace(m.group(2), m.group(1) or None),
        text
    )

    # ![url] — bare image/file shorthand
    text = re.sub(
        r'!\[([^\]]+)\]',
        lambda m: _media_replace(m.group(1)),
        text
    )

    # [url|text] custom link syntax — LEFT = url, RIGHT = visible text
    text = re.sub(
        r'\[([^\|\[\]]+)\|([^\[\]]+)\]',
        lambda m: f'[{m.group(2).strip()}]({m.group(1).strip()})',
        text
    )

    # [url] bare bracketed URL
    text = re.sub(
        r'(?<!!)\[(https?://[^\[\]]+)\]',
        lambda m: f'[{m.group(1).strip()}]({m.group(1).strip()})',
        text
    )

    html = markdown.markdown(
        text,
        extensions=['fenced_code', 'nl2br', 'sane_lists', 'tables']
    )

    # Restore LaTeX
    for key, value in placeholders.items():
        html = html.replace(key, value)

    return mark_safe(html)


@register.filter(name='strip_images')
def strip_images(text):
    """Remove markdown image/file syntax and URL-only lines for clean text preview."""
    if not text:
        return ''
    # Remove ![alt](url) and ![url]
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'!\[[^\]]+\]', '', text)
    # Remove lines that are only a URL (media paths)
    text = re.sub(r'(?m)^/?media/\S+$', '', text)
    # Remove markdown headings syntax (keep text)
    text = re.sub(r'(?m)^#{1,6}\s+', '', text)
    # Remove bold/italic markers
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


@register.filter(name='get_first_image')
def get_first_image(text):
    """Extract the first valid image URL from markdown content."""
    if not text:
        return None
    
    # 1. Look for standard markdown: ![alt](url)
    # We use a more specific pattern for the URL part to avoid greedy matching issues
    # and ensure it ends with an image extension.
    img_ext_pattern = r'\.(?:' + '|'.join(IMAGE_EXTS) + r')(?:\?.*|#.*)?$'
    
    # Match standard ![alt](url)
    matches = re.finditer(r'!\[.*?\]\((https?://\S+?|/media/\S+?)\)', text, re.IGNORECASE)
    for m in matches:
        url = m.group(1).strip()
        if re.search(img_ext_pattern, url, re.IGNORECASE):
            return url
            
    # 2. Look for our short syntax: ![url]
    matches = re.finditer(r'!\[(https?://[^\s\]]+|/media/[^\s\]]+)\]', text, re.IGNORECASE)
    for m in matches:
        url = m.group(1).strip()
        if re.search(img_ext_pattern, url, re.IGNORECASE):
            return url
            
    return None
