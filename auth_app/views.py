import secrets
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

from apps.models import Restaurant, UserProfile
from .forms import SignupForm
from .emails import send_verification_email, send_new_restaurant_notification


def signup(request):
    """Регистрация нового ресторана"""
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            # Создаём пользователя (неактивного до подтверждения email)
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password1'],
                is_active=False  # активируем после подтверждения email
            )
            
            # Генерируем slug ресторана
            slug = slugify(data['restaurant_name'], allow_unicode=False)
            if not slug:
                slug = f"restoran-{user.id}"
            
            # Проверяем уникальность slug
            base_slug = slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Создаём ресторан
            restaurant = Restaurant.objects.create(
                name=data['restaurant_name'],
                slug=slug,
                phone=data['phone'],
                address=data.get('address', ''),
                owner=user,
                status='pending_email'
            )
            
            # Создаём профиль
            token = secrets.token_urlsafe(32)
            profile = UserProfile.objects.create(
                user=user,
                restaurant=restaurant,
                role='owner',
                phone=data['phone'],
                email_verified=False,
                email_verification_token=token,
                email_verification_sent_at=timezone.now()
            )
            
            # Отправляем письмо с подтверждением
            try:
                send_verification_email(user, profile, request)
                messages.success(
                    request,
                    f'Регистрация успешна! Мы отправили письмо на {user.email}. '
                    'Проверьте почту и подтвердите email.'
                )
            except Exception as e:
                messages.warning(
                    request,
                    f'Регистрация успешна, но не удалось отправить письмо: {e}. '
                    'Свяжитесь с администратором.'
                )
            
            return redirect('auth_app:verify_email_sent')
    else:
        form = SignupForm()
    
    return render(request, 'auth_app/signup.html', {'form': form})


def verify_email_sent(request):
    """Страница «Проверьте почту»"""
    return render(request, 'auth_app/verify_email_sent.html')


def verify_email(request, token):
    """Подтверждение email по токену"""
    
    try:
        profile = UserProfile.objects.get(email_verification_token=token)
    except UserProfile.DoesNotExist:
        return render(request, 'auth_app/verify_email_error.html', {
            'error': 'Неверная или устаревшая ссылка.'
        })
    
    if profile.email_verified:
        return render(request, 'auth_app/verify_email_success.html', {
            'user': profile.user,
            'restaurant': profile.restaurant,
            'already': True
        })
    
    # Подтверждаем email
    profile.email_verified = True
    profile.email_verification_token = ''
    profile.save()
    
    # Активируем пользователя
    user = profile.user
    user.is_active = True
    user.save()
    
    # Меняем статус ресторана
    restaurant = profile.restaurant
    if restaurant.status == 'pending_email':
        restaurant.status = 'pending_moderation'
        restaurant.save()
    
    # Уведомляем администратора
    try:
        send_new_restaurant_notification(restaurant, request)
    except Exception:
        pass
    
    return render(request, 'auth_app/verify_email_success.html', {
        'user': user,
        'restaurant': restaurant,
        'already': False
    })