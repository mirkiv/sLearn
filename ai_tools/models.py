from django.db import models
from django.contrib.auth import get_user_model
from posts.models import Post

User = get_user_model()

class AIProviderSettings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20) # gemini, chatgpt, deepseek
    api_key = models.CharField(max_length=255, blank=True, default='')
    custom_prompt = models.TextField(blank=True, default='')
    language = models.CharField(max_length=10, default='default')
    ai_model = models.CharField(max_length=100, blank=True, default='')
    
    class Meta:
        unique_together = ('user', 'provider')

class AIHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)
    result_text = models.TextField()
    source_notes = models.ManyToManyField(Post, related_name='ai_histories')
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def parsed_data(self):
        import json, re
        clean_text = self.result_text.strip()
        
        # Handle JSON format
        if clean_text.startswith('{') or clean_text.startswith('```json'):
            if clean_text.startswith('```json'): clean_text = clean_text[7:]
            elif clean_text.startswith('```'): clean_text = clean_text[3:]
            if clean_text.endswith('```'): clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            try:
                data = json.loads(clean_text)
                return {
                    'comment': data.get('comment', ''),
                    'note': data.get('note', self.result_text)
                }
            except:
                pass
                
        # Handle XML tags
        comment_match = re.search(r'<comment>(.*?)</comment>', clean_text, re.DOTALL | re.IGNORECASE)
        note_match = re.search(r'<note>(.*?)</note>', clean_text, re.DOTALL | re.IGNORECASE)
        
        comment = comment_match.group(1).strip() if comment_match else ''
        
        if note_match:
            note = note_match.group(1).strip()
        elif comment_match:
            note = clean_text.replace(comment_match.group(0), '').strip()
        else:
            note = clean_text
            
        return {'comment': comment, 'note': note}

    @property
    def comment(self):
        return self.parsed_data['comment']
        
    @property
    def note(self):
        return self.parsed_data['note']
