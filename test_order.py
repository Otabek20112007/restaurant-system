"""
Скрипт для тестирования API создания заказа.
Запуск: python test_order.py
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from apps.models import Table, MenuItem


def test_create_order():
    # Берём первый столик
    table = Table.objects.first()
    if not table:
        print("❌ Нет столиков. Создайте хотя бы один в админке.")
        return
    
    print(f"🍽  Столик №{table.number}, токен: {table.qr_token}")
    
    # Берём два блюда
    items = MenuItem.objects.filter(is_available=True)[:2]
    if len(items) < 2:
        print("❌ Нужно минимум 2 блюда в меню.")
        return
    
    # Формируем заказ
    order_data = {
        "items": [
            {"menu_item_id": items[0].id, "quantity": 2},
            {"menu_item_id": items[1].id, "quantity": 1},
        ],
        "comment": "Тестовый заказ"
    }
    
    print(f"📦 Отправляем заказ: {json.dumps(order_data, ensure_ascii=False)}")
    
    # Отправляем через тестовый клиент Django
    client = Client()
    response = client.post(
        f'/api/order/{table.qr_token}/',
        data=json.dumps(order_data),
        content_type='application/json'
    )
    
    print(f"📡 HTTP статус: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print("✅ Заказ создан!")
        print(f"   ID заказа: {data['id']}")
        print(f"   Столик: {data['table_number']}")
        print(f"   Сумма: {data['total_price']}₽")
        print(f"   Статус: {data['status_display']}")
        print(f"   Позиции:")
        for item in data['items']:
            print(f"     - {item['quantity']}x {item['menu_item_name']} = {item['price']}₽")
    else:
        print(f"❌ Ошибка: {response.content.decode()}")


if __name__ == '__main__':
    test_create_order()