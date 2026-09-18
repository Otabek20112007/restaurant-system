import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

username = 'admin'
password = 'Admin2026!'  # ← поменяйте на свой пароль
email = 'admin@example.com'

if User.objects.filter(username=username).exists():
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print(f"✅ Пароль для '{username}' обновлён")
else:
    User.objects.create_superuser(
        username=username,
        password=password,
        email=email
    )
    print(f"✅ Суперпользователь '{username}' создан")

print(f"Логин: {username}")
print(f"Пароль: {password}")