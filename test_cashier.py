"""
Тест API кассы.
Запуск: python test_cashier.py
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from apps.models import Table, MenuItem


def test_cashier_api():
    client = Client()
    
    # 1. Логин
    print("1. Логин...")
    response = client.post(
        '/api/cashier/login/',
        data=json.dumps({'username': 'admin', 'password': 'Admin2026!'}),
        content_type='application/json'
    )
    print(f"   Статус: {response.status_code}")
    if response.status_code != 200:
        print(f"   ❌ Ошибка: {response.content.decode()}")
        return
    print(f"   ✅ Вход выполнен")
    
    # 2. Список заказов
    print("\n2. Получаем список заказов...")
    response = client.get('/api/cashier/orders/')
    print(f"   Статус: {response.status_code}")
    orders = response.json()
    print(f"   ✅ Найдено заказов: {len(orders)}")
    for order in orders[:3]:
        print(f"     - Заказ #{order['id']} — Стол {order['table_number']} — {order['total_price']}руб — {order['status_display']}")
    
    # 3. Список столов
    print("\n3. Получаем список столов...")
    response = client.get('/api/cashier/tables/')
    tables = response.json()
    print(f"   ✅ Найдено столов: {len(tables)}")
    for table in tables:
        status = "занят" if table['is_busy'] else "свободен"
        print(f"     - Стол №{table['number']} ({table['zone']}) — {status}")
    
    # 4. Создание заказа кассиром
    print("\n4. Создаём заказ от имени кассира...")
    if not tables:
        print("   ⚠️ Нет столов. Пропускаем.")
        return
    
    items = MenuItem.objects.filter(is_available=True)[:2]
    if len(items) < 2:
        print("   ⚠️ Нужно минимум 2 блюда. Пропускаем.")
        return
    
    # Ищем свободный стол
    free_table = next((t for t in tables if not t['is_busy']), tables[0])
    
    order_data = {
        "table_number": free_table['number'],
        "items": [
            {"menu_item_id": items[0].id, "quantity": 1},
            {"menu_item_id": items[1].id, "quantity": 2},
        ],
        "comment": "Заказ от кассира"
    }
    
    response = client.post(
        '/api/cashier/orders/create/',
        data=json.dumps(order_data),
        content_type='application/json'
    )
    print(f"   Статус: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"   ✅ Заказ #{data['id']} создан")
        print(f"      Стол: {data['table_number']}")
        print(f"      Сумма: {data['total_price']}руб")
        print(f"      Печать: {data.get('print_results', {})}")
    else:
        print(f"   ❌ Ошибка: {response.content.decode()}")
    
    # 5. Изменение статуса
    print("\n5. Меняем статус заказа на 'Готовится'...")
    if orders:
        order_id = orders[0]['id']
        response = client.patch(
            f'/api/cashier/orders/{order_id}/status/',
            data=json.dumps({'status': 'cooking'}),
            content_type='application/json'
        )
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Статус изменён на: {response.json()['status_display']}")


if __name__ == '__main__':
    test_cashier_api()