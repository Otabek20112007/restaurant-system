from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.views.decorators.csrf import csrf_exempt

from apps.models import Order, Table, MenuItem, Category, Printer, Agent
from .decorators import owner_required


def login_view(request):
    """Страница входа в кабинет"""
    if request.user.is_authenticated:
        # Проверяем, есть ли профиль и ресторан
        if (hasattr(request.user, 'profile') 
            and request.user.profile.restaurant):
            return redirect('dashboard:index')
        else:
            # Если профиля нет — выходим из аккаунта, чтобы войти другим
            logout(request)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Аккаунт не активирован. Подтвердите email.')
            else:
                login(request, user)
                
                # Проверяем, есть ли профиль и ресторан
                if (hasattr(user, 'profile') and user.profile.restaurant):
                    messages.success(request, f'Добро пожаловать, {user.username}!')
                    return redirect('dashboard:index')
                else:
                    messages.error(
                        request,
                        'У вас нет привязанного ресторана. '
                        'Обратитесь к администратору.'
                    )
                    logout(request)
        else:
            messages.error(request, 'Неверный логин или пароль')
    
    return render(request, 'dashboard/login.html')


def logout_view(request):
    """Выход из кабинета"""
    logout(request)
    messages.info(request, 'Вы вышли из кабинета')
    return redirect('dashboard:login')


@owner_required
def index(request):
    """Главная страница кабинета — обзор"""
    restaurant = request.restaurant
    
    # Статистика за сегодня
    today = timezone.now().date()
    today_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    )
    
    # Статистика за 7 дней
    week_ago = timezone.now() - timedelta(days=7)
    week_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__gte=week_ago
    )
    
    # Подсчёты
    context = {
        'restaurant': restaurant,
        'today_orders_count': today_orders.count(),
        'today_revenue': sum(o.total_price for o in today_orders.filter(status='paid')),
        'week_orders_count': week_orders.count(),
        'week_revenue': sum(o.total_price for o in week_orders.filter(status='paid')),
        'tables_count': Table.objects.filter(restaurant=restaurant).count(),
        'menu_items_count': MenuItem.objects.filter(restaurant=restaurant).count(),
        'categories_count': Category.objects.filter(restaurant=restaurant).count(),
        'printers_count': Printer.objects.filter(restaurant=restaurant).count(),
        'agents_count': Agent.objects.filter(restaurant=restaurant).count(),
        'recent_orders': Order.objects.filter(
            restaurant=restaurant
        ).order_by('-created_at')[:10],
        'days_left': restaurant.days_left,
    }
    
    return render(request, 'dashboard/index.html', context)

from django.shortcuts import get_object_or_404
from .forms import CategoryForm, MenuItemForm


# ============================================================
#                    РАЗДЕЛ «МЕНЮ»
# ============================================================

@owner_required
def menu_view(request):
    """Список категорий и блюд"""
    restaurant = request.restaurant
    
    categories = Category.objects.filter(
        restaurant=restaurant
    ).prefetch_related('items').order_by('sort_order', 'name')
    
    # Блюда без категории (если есть)
    items_without_category = MenuItem.objects.filter(
        restaurant=restaurant,
        category__isnull=True
    )
    
    context = {
        'restaurant': restaurant,
        'categories': categories,
        'items_without_category': items_without_category,
        'active': 'menu',
    }
    return render(request, 'dashboard/menu.html', context)


@owner_required
def category_create(request):
    """Создание категории"""
    restaurant = request.restaurant
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.restaurant = restaurant
            category.save()
            messages.success(request, f'Категория "{category.name}" создана')
            return redirect('dashboard:menu')
    else:
        form = CategoryForm()
    
    context = {
        'restaurant': restaurant,
        'form': form,
        'title': 'Новая категория',
        'active': 'menu',
    }
    return render(request, 'dashboard/category_form.html', context)


@owner_required
def category_edit(request, category_id):
    """Редактирование категории"""
    restaurant = request.restaurant
    category = get_object_or_404(Category, id=category_id, restaurant=restaurant)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Категория "{category.name}" обновлена')
            return redirect('dashboard:menu')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'restaurant': restaurant,
        'form': form,
        'category': category,
        'title': f'Редактировать: {category.name}',
        'active': 'menu',
    }
    return render(request, 'dashboard/category_form.html', context)


@owner_required
def category_delete(request, category_id):
    """Удаление категории"""
    restaurant = request.restaurant
    category = get_object_or_404(Category, id=category_id, restaurant=restaurant)
    
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Категория "{name}" удалена')
        return redirect('dashboard:menu')
    
    context = {
        'restaurant': restaurant,
        'category': category,
        'active': 'menu',
    }
    return render(request, 'dashboard/category_confirm_delete.html', context)


@owner_required
def item_create(request):
    """Создание блюда"""
    restaurant = request.restaurant
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, restaurant=restaurant)
        if form.is_valid():
            item = form.save(commit=False)
            item.restaurant = restaurant
            item.save()
            messages.success(request, f'Блюдо "{item.name}" создано')
            return redirect('dashboard:menu')
    else:
        form = MenuItemForm(restaurant=restaurant)
    
    context = {
        'restaurant': restaurant,
        'form': form,
        'title': 'Новое блюдо',
        'active': 'menu',
    }
    return render(request, 'dashboard/item_form.html', context)


@owner_required
def item_edit(request, item_id):
    """Редактирование блюда"""
    restaurant = request.restaurant
    item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=item, restaurant=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, f'Блюдо "{item.name}" обновлено')
            return redirect('dashboard:menu')
    else:
        form = MenuItemForm(instance=item, restaurant=restaurant)
    
    context = {
        'restaurant': restaurant,
        'form': form,
        'item': item,
        'title': f'Редактировать: {item.name}',
        'active': 'menu',
    }
    return render(request, 'dashboard/item_form.html', context)


@owner_required
def item_delete(request, item_id):
    """Удаление блюда"""
    restaurant = request.restaurant
    item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
    
    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f'Блюдо "{name}" удалено')
        return redirect('dashboard:menu')
    
    context = {
        'restaurant': restaurant,
        'item': item,
        'active': 'menu',
    }
    return render(request, 'dashboard/item_confirm_delete.html', context)

import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
from apps.models import Table


# ============================================================
#                    РАЗДЕЛ «СТОЛИКИ»
# ============================================================

def get_table_url(table, for_print=False):
    """
    Возвращает URL для QR-кода столика.
    for_print=True → production URL (для печати).
    for_print=False → локальный URL (для теста).
    """
    base = settings.SITE_URL_PROD if for_print else settings.SITE_URL_LOCAL
    return f"{base}/r/{table.restaurant.slug}/t/{table.qr_token}/"


@owner_required
def tables_view(request):
    """Список столиков"""
    restaurant = request.restaurant
    tables = Table.objects.filter(restaurant=restaurant).order_by('number')
    
    context = {
        'restaurant': restaurant,
        'tables': tables,
        'active': 'tables',
    }
    return render(request, 'dashboard/tables.html', context)


@owner_required
def table_create(request):
    """Создание столика"""
    restaurant = request.restaurant
    
    if request.method == 'POST':
        number = request.POST.get('number')
        zone = request.POST.get('zone', '')
        
        if not number:
            messages.error(request, 'Укажите номер столика')
        else:
            try:
                number = int(number)
                if Table.objects.filter(restaurant=restaurant, number=number).exists():
                    messages.error(request, f'Столик №{number} уже существует')
                else:
                    table = Table.objects.create(
                        restaurant=restaurant,
                        number=number,
                        zone=zone
                    )
                    messages.success(request, f'Столик №{table.number} создан')
                    return redirect('dashboard:tables')
            except ValueError:
                messages.error(request, 'Номер должен быть числом')
    
    context = {
        'restaurant': restaurant,
        'active': 'tables',
    }
    return render(request, 'dashboard/table_form.html', context)


@owner_required
def table_edit(request, table_id):
    """Редактирование столика"""
    restaurant = request.restaurant
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    
    if request.method == 'POST':
        number = request.POST.get('number')
        zone = request.POST.get('zone', '')
        
        if not number:
            messages.error(request, 'Укажите номер столика')
        else:
            try:
                number = int(number)
                existing = Table.objects.filter(restaurant=restaurant, number=number).exclude(id=table.id)
                if existing.exists():
                    messages.error(request, f'Столик №{number} уже существует')
                else:
                    table.number = number
                    table.zone = zone
                    table.save()
                    messages.success(request, f'Столик №{table.number} обновлён')
                    return redirect('dashboard:tables')
            except ValueError:
                messages.error(request, 'Номер должен быть числом')
    
    context = {
        'restaurant': restaurant,
        'table': table,
        'active': 'tables',
    }
    return render(request, 'dashboard/table_form.html', context)


@owner_required
def table_delete(request, table_id):
    """Удаление столика"""
    restaurant = request.restaurant
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    
    if request.method == 'POST':
        number = table.number
        table.delete()
        messages.success(request, f'Столик №{number} удалён')
        return redirect('dashboard:tables')
    
    context = {
        'restaurant': restaurant,
        'table': table,
        'active': 'tables',
    }
    return render(request, 'dashboard/table_confirm_delete.html', context)


@owner_required
def table_qr(request, table_id):
    """Показать QR-код столика"""
    restaurant = request.restaurant
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    
    # URL для теста (локальный)
    qr_url_local = get_table_url(table, for_print=False)
    
    # URL для печати (production)
    qr_url_prod = get_table_url(table, for_print=True)
    
    context = {
        'restaurant': restaurant,
        'table': table,
        'qr_url_local': qr_url_local,
        'qr_url_prod': qr_url_prod,
        'active': 'tables',
    }
    return render(request, 'dashboard/table_qr.html', context)


@owner_required
def table_qr_image(request, table_id):
    """Генерирует PNG с QR-кодом"""
    restaurant = request.restaurant
    table = get_object_or_404(Table, id=table_id, restaurant=restaurant)
    
    # Проверяем, какой URL использовать
    use_prod = request.GET.get('print') == '1'
    qr_url = get_table_url(table, for_print=use_prod)
    
    # Генерируем QR-код
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Отдаём как PNG
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return HttpResponse(buffer, content_type='image/png')

from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json


# ============================================================
#                    РАЗДЕЛ «ЗАКАЗЫ»
# ============================================================

@owner_required
def orders_view(request):
    """Список заказов ресторана"""
    restaurant = request.restaurant
    
    # Фильтр по статусу
    status_filter = request.GET.get('status', '')
    
    orders = Order.objects.filter(
        restaurant=restaurant
    ).select_related('table').prefetch_related('items__menu_item')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Только за сегодня (по умолчанию)
    show_all = request.GET.get('all') == '1'
    if not show_all:
        from django.utils import timezone
        today = timezone.now().date()
        orders = orders.filter(created_at__date=today)
    
    # Ограничиваем 100
    orders = orders[:100]
    
    # Подсчёт по статусам
    today = timezone.now().date()
    today_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    )
    
    status_counts = {
        'new': today_orders.filter(status='new').count(),
        'cooking': today_orders.filter(status='cooking').count(),
        'ready': today_orders.filter(status='ready').count(),
        'served': today_orders.filter(status='served').count(),
        'paid': today_orders.filter(status='paid').count(),
        'cancelled': today_orders.filter(status='cancelled').count(),
    }
    
    context = {
        'restaurant': restaurant,
        'orders': orders,
        'status_filter': status_filter,
        'status_counts': status_counts,
        'show_all': show_all,
        'active': 'orders',
    }
    return render(request, 'dashboard/orders.html', context)


@owner_required
def order_detail(request, order_id):
    """Детали заказа"""
    restaurant = request.restaurant
    order = get_object_or_404(
        Order.objects.select_related('table').prefetch_related('items__menu_item'),
        id=order_id,
        restaurant=restaurant
    )
    
    context = {
        'restaurant': restaurant,
        'order': order,
        'active': 'orders',
    }
    return render(request, 'dashboard/order_detail.html', context)


@owner_required
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
    
    # Если заказ оплачен — освобождаем столик
    if new_status in ['paid', 'cancelled'] and order.table:
        order.table.is_busy = False
        order.table.save()
    
    order.save()
    
    return JsonResponse({
        'status': 'ok',
        'order_status': order.status,
        'order_status_display': order.get_status_display(),
    })

# ============================================================
#                    РЕДАКТОР СХЕМЫ ЗАЛА
# ============================================================

@owner_required
def floor_plan_view(request):
    """Редактор схемы зала"""
    restaurant = request.restaurant
    tables = Table.objects.filter(restaurant=restaurant).order_by('number')
    
    context = {
        'restaurant': restaurant,
        'tables': tables,
        'active': 'floor_plan',
    }
    return render(request, 'dashboard/floor_plan.html', context)


@csrf_exempt
@owner_required
@require_POST
def floor_plan_save(request):
    """API: сохранить координаты столов"""
    restaurant = request.restaurant
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат'}, status=400)
    
    tables_data = data.get('tables', [])
    
    for table_data in tables_data:
        try:
            table = Table.objects.get(
                id=table_data['id'],
                restaurant=restaurant
            )
            table.position_x = table_data.get('position_x', table.position_x)
            table.position_y = table_data.get('position_y', table.position_y)
            table.width = table_data.get('width', table.width)
            table.height = table_data.get('height', table.height)
            table.shape = table_data.get('shape', table.shape)
            table.save()
        except Table.DoesNotExist:
            continue
    
    return JsonResponse({'status': 'ok', 'saved': len(tables_data)})