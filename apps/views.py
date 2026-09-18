from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Category, MenuItem, Table, Order, OrderItem, FailedPrintJob
from .serializers import (
    CategorySerializer, TableSerializer,
    OrderSerializer, CreateOrderSerializer
)
from django.contrib.auth import authenticate, login, logout


@api_view(['GET'])
def menu_view(request):
    """Получить полное меню"""
    categories = Category.objects.prefetch_related('items').all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def table_by_token(request, token):
    """Получить столик по QR-токену"""
    try:
        table = Table.objects.get(qr_token=token)
    except Table.DoesNotExist:
        return Response(
            {'error': 'Столик не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = TableSerializer(table)
    return Response(serializer.data)


@api_view(['POST'])
def create_order(request, token):
    """Создать заказ для столика"""
    try:
        table = Table.objects.get(qr_token=token)
    except Table.DoesNotExist:
        return Response(
            {'error': 'Столик не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    order = Order.objects.create(
        table=table,
        comment=serializer.validated_data.get('comment', '')
    )
    
    for item_data in serializer.validated_data['items']:
        try:
            menu_item = MenuItem.objects.get(
                id=item_data['menu_item_id'],
                is_available=True
            )
        except MenuItem.DoesNotExist:
            order.delete()
            return Response(
                {'error': f"Блюдо {item_data['menu_item_id']} недоступно"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=item_data['quantity'],
            price=menu_item.price
        )
    
    order.calculate_total()
    
    # Отправляем заказ на принтеры (если они настроены)
    from .printer_service import print_order_to_all_targets
    print_results = print_order_to_all_targets(order)
    
    table.is_busy = True
    table.save()
    
    return Response(
        {
            **OrderSerializer(order).data,
            'print_results': print_results,
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
def order_status(request, order_id):
    """Статус заказа"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    return Response({
        'id': order.id,
        'status': order.status,
        'status_display': order.get_status_display(),
        'total_price': order.total_price,
    })


@api_view(['GET'])
def failed_prints(request):
    """Список заказов, которые не напечатались — для кассы"""
    jobs = FailedPrintJob.objects.filter(
        is_resolved=False
    ).select_related('order', 'order__table')
    
    data = [
        {
            'id': job.id,
            'order_id': job.order.id,
            'table': job.order.table.number if job.order.table else None,
            'target': job.target,
            'reason': job.reason,
            'order_total': str(job.order.total_price),
            'created_at': job.created_at,
        }
        for job in jobs
    ]
    return Response(data)


@api_view(['POST'])
def resolve_failed_print(request, job_id):
    """Кассир обработал неудачную печать"""
    try:
        job = FailedPrintJob.objects.get(id=job_id)
    except FailedPrintJob.DoesNotExist:
        return Response(
            {'error': 'Запись не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    job.is_resolved = True
    job.save()
    return Response({'status': 'ok'})


    from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from .models import Printer
from .serializers import PrinterSerializer


# ============================================================
#                    API ДЛЯ КАССЫ
# ============================================================

@api_view(['POST'])
def cashier_login(request):
    """Вход кассира"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Укажите логин и пароль'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {'error': 'Неверный логин или пароль'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {'error': 'Пользователь заблокирован'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    login(request, user)
    return Response({
        'status': 'ok',
        'user': {
            'id': user.id,
            'username': user.username,
            'is_superuser': user.is_superuser,
        }
    })


@api_view(['POST'])
def cashier_logout(request):
    """Выход кассира"""
    logout(request)
    return Response({'status': 'ok'})


@api_view(['GET'])
def cashier_me(request):
    """Текущий пользователь"""
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Не авторизован'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    return Response({
        'id': request.user.id,
        'username': request.user.username,
        'is_superuser': request.user.is_superuser,
    })


@api_view(['GET'])
def cashier_orders(request):
    """
    Список всех заказов для кассы.
    Параметры:
      ?status=new  — фильтр по статусу
      ?table=5     — фильтр по столику
    """
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Не авторизован'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    orders = Order.objects.select_related('table').prefetch_related('items__menu_item')
    
    status_filter = request.query_params.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    table_filter = request.query_params.get('table')
    if table_filter:
        orders = orders.filter(table__number=table_filter)
    
    # Только за сегодня
    from django.utils import timezone
    today = timezone.now().date()
    orders = orders.filter(created_at__date=today)
    
    # Ограничиваем 100 последними
    orders = orders[:100]
    
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
def cashier_update_order_status(request, order_id):
    """Изменить статус заказа"""
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Не авторизован'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Заказ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    new_status = request.data.get('status')
    valid_statuses = [s[0] for s in Order.STATUS_CHOICES]
    
    if new_status not in valid_statuses:
        return Response(
            {'error': f'Неверный статус. Допустимые: {valid_statuses}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    order.status = new_status
    order.save()
    
    # Если заказ оплачен — освобождаем столик
    if new_status == 'paid' and order.table:
        order.table.is_busy = False
        order.table.save()
    
    serializer = OrderSerializer(order)
    return Response(serializer.data)


@api_view(['POST'])
def cashier_create_order(request):
    """
    Кассир создаёт заказ вручную.
    Тело запроса:
    {
      "table_number": 5,
      "items": [
        {"menu_item_id": 1, "quantity": 2},
        {"menu_item_id": 3, "quantity": 1}
      ],
      "comment": "Без лука"
    }
    """
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Не авторизован'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    table_number = request.data.get('table_number')
    items = request.data.get('items', [])
    comment = request.data.get('comment', '')
    
    if not table_number:
        return Response(
            {'error': 'Укажите номер столика'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not items:
        return Response(
            {'error': 'Заказ не может быть пустым'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        table = Table.objects.get(number=table_number)
    except Table.DoesNotExist:
        return Response(
            {'error': f'Столик №{table_number} не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    order = Order.objects.create(table=table, comment=comment)
    
    for item_data in items:
        try:
            menu_item = MenuItem.objects.get(
                id=item_data['menu_item_id'],
                is_available=True
            )
        except MenuItem.DoesNotExist:
            order.delete()
            return Response(
                {'error': f"Блюдо {item_data['menu_item_id']} недоступно"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=item_data['quantity'],
            price=menu_item.price
        )
    
    order.calculate_total()
    
    # Отправляем на принтеры
    from .printer_service import print_order_to_all_targets
    print_results = print_order_to_all_targets(order)
    
    table.is_busy = True
    table.save()
    
    return Response(
        {
            **OrderSerializer(order).data,
            'print_results': print_results,
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
def cashier_tables(request):
    """Список столов для кассы (со статусами)"""
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Не авторизован'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    tables = Table.objects.all()
    serializer = TableSerializer(tables, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def cashier_printers(request):
    """Список принтеров"""
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Не авторизован'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    printers = Printer.objects.all()
    serializer = PrinterSerializer(printers, many=True)
    return Response(serializer.data)