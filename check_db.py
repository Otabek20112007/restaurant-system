"""Проверка, какие таблицы есть в базе"""
import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

db_path = settings.DATABASES['default']['NAME']
print(f"База данных: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [row[0] for row in cursor.fetchall()]

print("\nТаблицы в базе:")
for table in tables:
    marker = " ← ✅" if 'userprofile' in table.lower() else ""
    print(f"  {table}{marker}")

conn.close()

if any('userprofile' in t.lower() for t in tables):
    print("\n✅ Таблица apps_userprofile существует!")
else:
    print("\n❌ Таблица apps_userprofile НЕ найдена!")