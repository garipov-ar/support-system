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
