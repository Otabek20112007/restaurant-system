import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from apps.models import Restaurant, Table, Category, MenuItem, Order, OrderItem


def table_menu(request, restaurant_slug, token):
    """
    Клиентское меню для столика.
    URL: /r/<slug>/t/<token>/
    """
    # Находим ресторан
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
    
    # Проверяем, что ресторан активен
    if not restaurant.is_active_now:
        return render(request, 'client/inactive.html', {
            'restaurant': restaurant
        })
    
    # Находим столик по токену
    table = get_object_or_404(Table, qr_token=token, restaurant=restaurant)
    
    # Меню: категории с блюдами
    categories = Category.objects.filter(
        restaurant=restaurant
    ).prefetch_related(
        'items'
    ).order_by('sort_order', 'name')
    
    # Блюда без категории
    items_without_category = MenuItem.objects.filter(
        restaurant=restaurant,
        category__isnull=True,
        is_available=True
    )
    
    context = {
        'restaurant': restaurant,
        'table': table,
        'categories': categories,
        'items_without_category': items_without_category,
        'currency': restaurant.currency,
    }
    return render(request, 'client/menu.html', context)


@require_POST
def create_order(request, restaurant_slug, token):
    """
    API: создание заказа.
    URL: /r/<slug>/t/<token>/order/
    """
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
    
    if not restaurant.is_active_now:
        return JsonResponse({
            'error': 'Ресторан временно не принимает заказы'
        }, status=403)
    
    table = get_object_or_404(Table, qr_token=token, restaurant=restaurant)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    
    items = data.get('items', [])
    comment = data.get('comment', '').strip()
    
    if not items:
        return JsonResponse({'error': 'Корзина пуста'}, status=400)
    
    # Проверяем все блюда
    menu_item_ids = [item.get('menu_item_id') for item in items]
    menu_items = {
        mi.id: mi for mi in MenuItem.objects.filter(
            id__in=menu_item_ids,
            restaurant=restaurant,
            is_available=True
        )
    }
    
    if len(menu_items) != len(menu_item_ids):
        return JsonResponse({
            'error': 'Некоторые блюда недоступны'
        }, status=400)
    
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
        
        # Отмечаем столик как занятый
        table.is_busy = True
        table.save()
    
    # Отправляем на принтеры (если настроены)
    from apps.printer_service import print_order_to_all_targets
    try:
        print_results = print_order_to_all_targets(order)
    except Exception as e:
        print_results = {'error': str(e)}
    
    return JsonResponse({
        'status': 'ok',
        'order_id': order.id,
        'total_price': str(order.total_price),
        'print_results': print_results,
    })


def order_status(request, restaurant_slug, order_id):
    """
    Страница статуса заказа.
    URL: /r/<slug>/order/<order_id>/
    """
    restaurant = get_object_or_404(Restaurant, slug=restaurant_slug)
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)
    
    context = {
        'restaurant': restaurant,
        'order': order,
    }
    return render(request, 'client/order_status.html', context)