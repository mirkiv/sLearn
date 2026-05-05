from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import re

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        label="Ник (Отображаемое имя)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Твой ник'})
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'email')
        labels = {
            'username': 'Юзернейм',
            'email': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = "Пароль"
        self.fields['password2'].label = "Подтверждение пароля"

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            return username
            
        # Ensure @ is only at the beginning
        if username.count('@') > 1:
            raise forms.ValidationError("Username can only contain one '@' symbol.")
        if '@' in username and not username.startswith('@'):
            raise forms.ValidationError("The '@' symbol can only be at the beginning.")
            
        import re
        if not re.match(r'^@?[\w.+-]+$', username):
            raise forms.ValidationError("Username contains invalid characters. Use letters, numbers, and . + - _")
            
        return username

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Юзернейм'}), label="Юзернейм")
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}), label="Пароль")

class ProfileEditForm(forms.ModelForm):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.lang = kwargs.pop('lang', 'ru')
        super().__init__(*args, **kwargs)
        from posts.templatetags.custom_dict import t_py
        self.fields['username'].widget.attrs['placeholder'] = t_py('username', self.lang)
        self.fields['first_name'].widget.attrs['placeholder'] = t_py('first_name', self.lang)
        self.fields['current_password'].widget.attrs['placeholder'] = t_py('current_password', self.lang)
        # We don't set label here because template uses {% t field.name %}

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'avatar']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        current_password = cleaned_data.get('current_password')

        if self.instance and self.instance.pk:
            username_changed = username != self.instance.username
            email_changed = email != self.instance.email

            if username_changed or email_changed:
                if not current_password:
                    from posts.templatetags.custom_dict import t_py
                    self.add_error('current_password', t_py('error_current_password_required', self.lang))
                else:
                    if not self.instance.check_password(current_password):
                        from posts.templatetags.custom_dict import t_py
                        self.add_error('current_password', t_py('invalid_password', self.lang))
        return cleaned_data
