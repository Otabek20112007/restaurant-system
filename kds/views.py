from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from functools import wraps
import json

from apps.models import Order, OrderItem


def kds_login(request):
    """Вход в KDS"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.restaurant:
            return redirect('kds:index')
        else:
            logout(request)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Аккаунт не активирован.')
            elif not hasattr(user, 'profile') or not user.profile.restaurant:
                messages.error(request, 'У вас нет привязанного ресторана.')
            else:
                login(request, user)
                return redirect('kds:index')
        else:
            messages.error(request, 'Неверный логин или пароль')
    
    return render(request, 'kds/login.html')


def kds_logout(request):
    """Выход из KDS"""
    logout(request)
    return redirect('kds:login')


def kds_required(view_func):
    """Декоратор для KDS"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('kds:login')
        
        if not hasattr(request.user, 'profile') or not request.user.profile.restaurant:
            messages.error(request, 'У вас нет привязанного ресторана.')
            logout(request)
            return redirect('kds:login')
        
        request.restaurant = request.user.profile.restaurant
        return view_func(request, *args, **kwargs)
    
    return wrapper


@kds_required
def index(request):
    """Главный экран KDS"""
    restaurant = request.restaurant
    
    context = {
        'restaurant': restaurant,
    }
    return render(request, 'kds/index.html', context)


@kds_required
def orders_api(request):
    """
    API: список активных заказов для кухни.
    Возвращает только заказы со статусами new и cooking.
    """
    restaurant = request.restaurant
    
    # Активные заказы: новые + готовится
    orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=['new', 'cooking']
    ).select_related('table').prefetch_related('items__menu_item').order_by('created_at')
    
    data = []
    for order in orders:
        # Считаем, сколько времени прошло
        elapsed_minutes = int((timezone.now() - order.created_at).total_seconds() / 60)
        
        data.append({
            'id': order.id,
            'table_number': order.table.number if order.table else None,
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': order.created_at.strftime('%H:%M'),
            'elapsed_minutes': elapsed_minutes,
            'comment': order.comment,
            'items': [
                {
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'comment': '',  # пока пусто
                }
                for item in order.items.all()
            ],
        })
    
    return JsonResponse({
        'orders': data,
        'count': len(data),
        'new_count': orders.filter(status='new').count(),
        'cooking_count': orders.filter(status='cooking').count(),
    })


@csrf_exempt
@kds_required
@require_POST
def order_change_status(request, order_id):
    """API: изменить статус заказа"""
    restaurant = request.restaurant
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат'}, status=400)
    
    new_status = data.get('status')
    
    # Разрешаем только new → cooking → ready
    if new_status not in ['cooking', 'ready']:
        return JsonResponse({'error': 'Неверный статус'}, status=400)
    
    order.status = new_status
    order.save()
    
    return JsonResponse({
        'status': 'ok',
        'order_status': order.status,
        'order_status_display': order.get_status_display(),
    })