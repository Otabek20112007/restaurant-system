from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404

from apps.models import Order, OrderItem, Table, MenuItem, Category, FailedPrintJob


def cashier_login(request):
    """Вход кассира"""
    if request.user.is_authenticated:
        # Проверяем, есть ли профиль и ресторан
        if (hasattr(request.user, 'profile') and request.user.profile.restaurant):
            return redirect('cashier:index')
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
                return redirect('cashier:index')
        else:
            messages.error(request, 'Неверный логин или пароль')
    
    return render(request, 'cashier/login.html')


def cashier_logout(request):
    """Выход кассира"""
    logout(request)
    return redirect('cashier:login')


def cashier_required(view_func):
    """Декоратор для проверки, что у пользователя есть ресторан"""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('cashier:login')
        
        if not hasattr(request.user, 'profile') or not request.user.profile.restaurant:
            messages.error(request, 'У вас нет привязанного ресторана.')
            logout(request)
            return redirect('cashier:login')
        
        request.restaurant = request.user.profile.restaurant
        return view_func(request, *args, **kwargs)
    
    return wrapper


@cashier_required
def index(request):
    """Главный экран кассы"""
    restaurant = request.restaurant
    
    # Заказы за сегодня, кроме отменённых
    today = timezone.now().date()
    orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    ).exclude(
        status='cancelled'
    ).select_related('table').prefetch_related('items__menu_item').order_by('-created_at')
    
    # Подсчёт по статусам
    status_counts = {
        'new': orders.filter(status='new').count(),
        'cooking': orders.filter(status='cooking').count(),
        'ready': orders.filter(status='ready').count(),
        'served': orders.filter(status='served').count(),
    }
    
    # Неудачные печати
    failed_prints_count = FailedPrintJob.objects.filter(
        restaurant=restaurant,
        is_resolved=False
    ).count()
    
    context = {
        'restaurant': restaurant,
        'orders': orders,
        'status_counts': status_counts,
        'failed_prints_count': failed_prints_count,
    }
    return render(request, 'cashier/index.html', context)


@cashier_required
def orders_api(request):
    """API: список заказов для автообновления"""
    restaurant = request.restaurant
    
    today = timezone.now().date()
    orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    ).exclude(
        status='cancelled'
    ).select_related('table').prefetch_related('items__menu_item').order_by('-created_at')
    
    data = []
    for order in orders:
        data.append({
            'id': order.id,
            'table_number': order.table.number if order.table else None,
            'table_zone': order.table.zone if order.table else '',
            'status': order.status,
            'status_display': order.get_status_display(),
            'total_price': str(order.total_price),
            'comment': order.comment,
            'created_at': order.created_at.strftime('%H:%M'),
            'items': [
                {
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'price': str(item.price),
                    'subtotal': str(item.price * item.quantity),
                    'image': item.menu_item.image.url if item.menu_item.image else None,
                }
                for item in order.items.all()
            ],
        })
    
    return JsonResponse({
        'orders': data,
        'count': len(data),
    })


@cashier_required
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
    valid_statuses = [s[0] for s in Order.STATUS_CHOICES]
    
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Неверный статус'}, status=400)
    
    order.status = new_status
    
    # Если заказ оплачен или отменён — освобождаем столик
    if new_status in ['paid', 'cancelled'] and order.table:
        order.table.is_busy = False
        order.table.save()
    
    order.save()
    
    return JsonResponse({
        'status': 'ok',
        'order_status': order.status,
        'order_status_display': order.get_status_display(),
    })


@cashier_required
def tables_api(request):
    """API: список столов для ручного создания заказа"""
    restaurant = request.restaurant
    tables = Table.objects.filter(restaurant=restaurant).order_by('number')
    
    return JsonResponse({
        'tables': [
            {
                'id': t.id,
                'number': t.number,
                'zone': t.zone,
                'is_busy': t.is_busy,
            }
            for t in tables
        ]
    })


@cashier_required
def menu_api(request):
    """API: меню для ручного создания заказа"""
    restaurant = request.restaurant
    
    categories = Category.objects.filter(
        restaurant=restaurant
    ).prefetch_related('items').order_by('sort_order', 'name')
    
    data = []
    for category in categories:
        items = category.items.filter(is_available=True)
        if items:
            data.append({
                'id': category.id,
                'name': category.name,
                'items': [
                    {
                        'id': item.id,
                        'name': item.name,
                        'price': str(item.price),
                    }
                    for item in items
                ]
            })
    
    return JsonResponse({'categories': data})


@cashier_required
@require_POST
def create_order_manual(request):
    """API: создать заказ вручную (кассир)"""
    restaurant = request.restaurant
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат'}, status=400)
    
    table_id = data.get('table_id')
    items = data.get('items', [])
    comment = data.get('comment', '').strip()
    
    if not table_id:
        return JsonResponse({'error': 'Укажите столик'}, status=400)
    
    if not items:
        return JsonResponse({'error': 'Заказ не может быть пустым'}, status=400)
    
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    
    # Проверяем блюда
    menu_item_ids = [item.get('menu_item_id') for item in items]
    menu_items = {
        mi.id: mi for mi in MenuItem.objects.filter(
            id__in=menu_item_ids,
            restaurant=restaurant,
            is_available=True
        )
    }
    
    if len(menu_items) != len(menu_item_ids):
        return JsonResponse({'error': 'Некоторые блюда недоступны'}, status=400)
    
    # Создаём заказ в транзакции
    with transaction.atomic():
        order = Order.objects.create(
            restaurant=restaurant,
            table=table,
            comment=comment,
            status='new'
        )
        
        for item_data in items:
            menu_item = menu_items[item_data['menu_item_id']]
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data.get('quantity', 1),
                price=menu_item.price
            )
        
        order.calculate_total()
        
        table.is_busy = True
        table.save()
    
    # Отправляем на принтеры
    from apps.printer_service import print_order_to_all_targets
    try:
        print_results = print_order_to_all_targets(order)
    except Exception as e:
        print_results = {'error': str(e)}
    
    return JsonResponse({
        'status': 'ok',
        'order_id': order.id,
        'total_price': str(order.total_price),
    })


@cashier_required
def failed_prints_api(request):
    """API: неудачные печати"""
    restaurant = request.restaurant
    jobs = FailedPrintJob.objects.filter(
        restaurant=restaurant,
        is_resolved=False
    ).select_related('order', 'order__table')
    
    return JsonResponse({
        'jobs': [
            {
                'id': job.id,
                'order_id': job.order.id,
                'table': job.order.table.number if job.order.table else None,
                'target': job.target,
                'reason': job.reason,
                'created_at': job.created_at.strftime('%H:%M'),
            }
            for job in jobs
        ]
    })


@cashier_required
@require_POST
def resolve_failed_print(request, job_id):
    """Отметить неудачную печать как обработанную"""
    restaurant = request.restaurant
    job = get_object_or_404(FailedPrintJob, id=job_id, restaurant=restaurant)
    job.is_resolved = True
    job.save()
    return JsonResponse({'status': 'ok'})

@cashier_required
def tables_with_status_api(request):
    """
    API: столы с информацией об активных заказах.
    Возвращает координаты, статус, сумму заказа.
    """
    restaurant = request.restaurant
    
    tables = Table.objects.filter(restaurant=restaurant).order_by('number')
    
    data = []
    for table in tables:
        # Ищем активный заказ на этом столе
        active_order = Order.objects.filter(
            restaurant=restaurant,
            table=table,
            status__in=['new', 'cooking', 'ready', 'served']
        ).order_by('-created_at').first()
        
        table_data = {
            'id': table.id,
            'number': table.number,
            'zone': table.zone,
            'position_x': table.position_x,
            'position_y': table.position_y,
            'width': table.width,
            'height': table.height,
            'shape': table.shape,
            'is_busy': table.is_busy,
        }
        
        if active_order:
            table_data.update({
                'has_order': True,
                'order_id': active_order.id,
                'order_status': active_order.status,
                'order_status_display': active_order.get_status_display(),
                'order_total': str(active_order.total_price),
                'order_time': active_order.created_at.strftime('%H:%M'),
            })
        else:
            table_data.update({
                'has_order': False,
                'order_id': None,
                'order_status': None,
                'order_status_display': 'Свободен',
                'order_total': None,
                'order_time': None,
            })
        
        data.append(table_data)
    
    return JsonResponse({'tables': data})

from django.views.decorators.csrf import csrf_exempt


@cashier_required
def order_fullscreen(request, order_id):
    """Полноэкранное окно заказа (как в iiko)"""
    restaurant = request.restaurant
    order = get_object_or_404(
        Order.objects.select_related('table').prefetch_related('items__menu_item'),
        id=order_id,
        restaurant=restaurant
    )
    
    categories = Category.objects.filter(
        restaurant=restaurant
    ).prefetch_related('items').order_by('sort_order', 'name')
    
    context = {
        'restaurant': restaurant,
        'order': order,
        'categories': categories,
    }
    return render(request, 'cashier/order.html', context)


@csrf_exempt
@cashier_required
@require_POST
def order_add_item(request, order_id):
    """API: добавить блюдо в заказ"""
    restaurant = request.restaurant
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат'}, status=400)
    
    menu_item_id = data.get('menu_item_id')
    if not menu_item_id:
        return JsonResponse({'error': 'Не указано блюдо'}, status=400)
    
    try:
        menu_item = MenuItem.objects.get(
            id=menu_item_id,
            restaurant=restaurant,
            is_available=True
        )
    except MenuItem.DoesNotExist:
        return JsonResponse({'error': 'Блюдо недоступно'}, status=404)
    
    # Ищем такую позицию в заказе
    order_item, created = OrderItem.objects.get_or_create(
        order=order,
        menu_item=menu_item,
        defaults={'quantity': 1, 'price': menu_item.price}
    )
    
    if not created:
        order_item.quantity += 1
        order_item.save()
    
    order.calculate_total()
    
    # === ПОМЕЧАЕМ СТОЛ ЗАНЯТЫМ ===
    if order.table:
        order.table.is_busy = True
        order.table.save()
    # === КОНЕЦ ===
    
    return JsonResponse({
        'status': 'ok',
        'order_item_id': order_item.id,
        'quantity': order_item.quantity,
    })


@csrf_exempt
@cashier_required
@require_POST
def order_change_qty(request, order_id):
    """API: изменить количество блюда"""
    restaurant = request.restaurant
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат'}, status=400)
    
    order_item_id = data.get('order_item_id')
    delta = data.get('delta', 0)
    
    try:
        order_item = OrderItem.objects.get(id=order_item_id, order=order)
    except OrderItem.DoesNotExist:
        return JsonResponse({'error': 'Позиция не найдена'}, status=404)
    
    order_item.quantity += delta
    
    if order_item.quantity <= 0:
        order_item.delete()
        order.calculate_total()
        return JsonResponse({
            'status': 'ok',
            'removed': True,
            'total': str(order.total_price),
        })
    
    order_item.save()
    order.calculate_total()
    
    return JsonResponse({
        'status': 'ok',
        'removed': False,
        'quantity': order_item.quantity,
        'subtotal': str(order_item.price * order_item.quantity),
        'total': str(order.total_price),
    })

@cashier_required
def table_fullscreen(request, table_id):
    """
    Полноэкранное окно для стола.
    Если есть активный заказ — открываем его.
    Если нет — создаём новый пустой заказ.
    """
    restaurant = request.restaurant
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    
    # Ищем активный заказ на этом столе
    active_order = Order.objects.filter(
        restaurant=restaurant,
        table=table,
        status__in=['new', 'cooking', 'ready', 'served']
    ).order_by('-created_at').first()
    
    # Если нет — создаём новый пустой заказ
    if not active_order:
        active_order = Order.objects.create(
            restaurant=restaurant,
            table=table,
            status='new',
            total_price=0
        )
        # НЕ помечаем стол занятым, пока не добавят блюдо
    
    # Перенаправляем на полноэкранное окно заказа
    return redirect('cashier:order_fullscreen', order_id=active_order.id)