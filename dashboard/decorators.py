from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout


def owner_required(view_func):
    """
    Декоратор: пропускает только владельцев ресторанов.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1. Авторизован?
        if not request.user.is_authenticated:
            return redirect('dashboard:login')
        
        # 2. Есть профиль?
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'У вас нет профиля. Обратитесь к администратору.')
            logout(request)  # ← выходим, чтобы не было цикла
            return redirect('dashboard:login')
        
        profile = request.user.profile
        
        # 3. Есть ресторан?
        if not profile.restaurant:
            messages.error(request, 'У вас нет привязанного ресторана.')
            logout(request)  # ← выходим
            return redirect('dashboard:login')
        
        # 4. Роль подходит?
        if profile.role not in ['owner', 'manager', 'super_admin']:
            messages.error(request, 'У вас нет доступа к кабинету.')
            logout(request)
            return redirect('dashboard:login')
        
        # 5. Ресторан активен?
        if not profile.restaurant.is_active_now:
            messages.warning(
                request,
                f'Ваш ресторан сейчас неактивен. Статус: {profile.restaurant.get_status_display()}'
            )
        
        # Сохраняем ресторан в request
        request.restaurant = profile.restaurant
        
        return view_func(request, *args, **kwargs)
    
    return wrapper