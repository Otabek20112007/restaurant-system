from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from apps.models import Restaurant


class SignupForm(forms.Form):
    """Форма регистрации ресторана"""
    
    # Данные ресторана
    restaurant_name = forms.CharField(
        max_length=200,
        label='Название ресторана',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: Пиццерия Ромашка'
        })
    )
    phone = forms.CharField(
        max_length=20,
        label='Телефон',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+992 90 123 45 67'
        })
    )
    address = forms.CharField(
        required=False,
        label='Адрес',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'г. Душанбе, ул. Рудаки 1'
        })
    )
    
    # Данные владельца
    username = forms.CharField(
        max_length=150,
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ivan_petrov'
        })
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ivan@example.com'
        })
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Минимум 8 символов'
        })
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    )
    
    agree = forms.BooleanField(
        label='Согласен с условиями',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Такой логин уже занят')
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError('Этот email уже зарегистрирован')
        return email
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают')
        if password2 and len(password2) < 8:
            raise ValidationError('Пароль должен быть минимум 8 символов')
        return password2
    
    def clean_agree(self):
        agree = self.cleaned_data['agree']
        if not agree:
            raise ValidationError('Нужно согласиться с условиями')
        return agree