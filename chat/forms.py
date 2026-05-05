from django import forms
from .models import Message


class MessageForm(forms.ModelForm):
    text = forms.CharField(required=False, widget=forms.Textarea(
        attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type a message...'}
    ))

    class Meta:
        model = Message
        fields = ['text']
