from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class ClientRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(required=True, label="Имя")
    last_name = forms.CharField(required=True, label="Фамилия")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")
        
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Look for existing Telegram Bot user by email
        from apps.bot.models import BotUser
        # We assume email has been inputted since required=True
        bot_user = BotUser.objects.filter(email__iexact=user.email).first()
        if bot_user:
            user.telegram_id = bot_user.telegram_id
            
        if commit:
            user.save()
            
        return user
class SupportRequestForm(forms.ModelForm):
    class Meta:
        from apps.bot.models import SupportRequest
        model = SupportRequest
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Опишите вашу проблему...',
                'rows': 5,
                'style': 'width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; font-family: inherit;'
            }),
        }
