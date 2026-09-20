from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


def send_verification_email(user, profile, request=None):
    """Отправляет письмо с ссылкой подтверждения email"""
    
    token = profile.email_verification_token
    
    # Формируем ссылку
    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    else:
        base_url = settings.SITE_URL
    
    verify_url = f"{base_url}{reverse('auth_app:verify_email', args=[token])}"
    
    subject = 'Подтверждение регистрации'
    message = f"""
Здравствуйте, {user.username}!

Вы зарегистрировали ресторан в системе Restaurant System.

Для подтверждения email перейдите по ссылке:
{verify_url}

Если вы не регистрировались — просто проигнорируйте это письмо.

--
С уважением,
Команда Restaurant System
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_new_restaurant_notification(restaurant, request=None):
    """Отправляет уведомление администратору о новом ресторане"""
    
    if request:
        base_url = request.build_absolute_uri('/')[:-1]
    else:
        base_url = settings.SITE_URL
    
    admin_url = f"{base_url}/admin/apps/restaurant/{restaurant.id}/change/"
    
    subject = f'Новый ресторан: {restaurant.name}'
    message = f"""
Новый ресторан ожидает модерации.

Название: {restaurant.name}
Slug: {restaurant.slug}
Телефон: {restaurant.phone}
Адрес: {restaurant.address}
Владелец: {restaurant.owner.username if restaurant.owner else '-'}
Email владельца: {restaurant.owner.email if restaurant.owner else '-'}

Проверить и одобрить:
{admin_url}

--
Restaurant System
    """
    
    admin_email = settings.EMAIL_HOST_USER
    if admin_email:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=True,
        )