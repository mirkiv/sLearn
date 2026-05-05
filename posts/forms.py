from django import forms
from .models import Post, NoteChapter, Attachment

class PostForm(forms.ModelForm):
    hashtags_input = forms.CharField(
        required=True, 
        help_text="Enter hashtags separated by spaces (e.g. #math #physics)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '#study #math'})
    )

    class Meta:
        model = Post
        fields = ['post_type', 'title', 'content', 'group', 'visibility']
        widgets = {
            'post_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Title (Optional for simple posts)'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your thoughts or question...'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
        }

class NoteChapterForm(forms.ModelForm):
    class Meta:
        model = NoteChapter
        fields = ['title', 'text_content', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chapter Title (optional)'}),
            'text_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your section notes here...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
