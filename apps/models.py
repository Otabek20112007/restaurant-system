from django.db import models
from django.utils.text import slugify
import secrets


def generate_qr_token():
    """Генерирует случайный токен для QR-кода столика"""
    return secrets.token_urlsafe(16)


def generate_agent_token():
    """Генерирует токен для агента (Raspberry Pi)"""
    return secrets.token_urlsafe(32)


def generate_restaurant_db_name(slug):
    """Генерирует имя БД для ресторана (на будущее, для Подхода 2)"""
    return f"rest_{slug.replace('-', '_')}"


class Restaurant(models.Model):
    """Ресторан (тенант системы)"""
    
    STATUS_CHOICES = [
        ('pending_email', 'Ожидает подтверждения email'),
        ('pending_moderation', 'На модерации'),
        ('rejected', 'Отклонён'),
        ('trial', 'Пробный период'),
        ('active', 'Активен'),
        ('suspended', 'Заблокирован'),
        ('expired', 'Подписка истекла'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='URL-идентификатор',
        help_text='Латиница, без пробелов. Например: restoran-abc'
    )
    
    # Контакты
    address = models.TextField(blank=True, verbose_name='Адрес')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    
    # Дизайн
    logo = models.ImageField(
        upload_to='restaurants/logos/',
        blank=True,
        null=True,
        verbose_name='Логотип'
    )
    primary_color = models.CharField(
        max_length=7,
        default='#4CAF50',
        verbose_name='Основной цвет'
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#FFFFFF',
        verbose_name='Дополнительный цвет'
    )
    
    # Настройки
    currency = models.CharField(
        max_length=3,
        default='TJS',
        verbose_name='Валюта'
    )
    language = models.CharField(
        max_length=5,
        default='ru',
        verbose_name='Язык'
    )
    
    # Статус и подписка
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending_email',
        verbose_name='Статус'
    )
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Триал закончится'
    )
    paid_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Оплачено до'
    )
    
    # Владелец
    owner = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_restaurants',
        verbose_name='Владелец'
    )
    
    # Модерация
    moderation_note = models.TextField(
        blank=True,
        verbose_name='Заметка модератора'
    )
    moderated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата модерации'
    )
    moderated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_restaurants',
        verbose_name='Модератор'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    
    class Meta:
        verbose_name = 'Ресторан'
        verbose_name_plural = 'Рестораны'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} [{self.get_status_display()}]"
    
    @property
    def is_active_now(self):
        """Ресторан работает прямо сейчас?"""
        from django.utils import timezone
        if self.status == 'active':
            return True
        if self.status == 'trial':
            return self.trial_ends_at and self.trial_ends_at > timezone.now()
        return False
    
    @property
    def days_left(self):
        """Сколько дней осталось до конца триала"""
        from django.utils import timezone
        if self.status != 'trial' or not self.trial_ends_at:
            return 0
        delta = self.trial_ends_at - timezone.now()
        return max(0, delta.days)
    
    def approve(self, moderator, days_trial=7):
        """Одобрить ресторан и запустить триал"""
        from django.utils import timezone
        from datetime import timedelta
        
        self.status = 'trial'
        self.trial_ends_at = timezone.now() + timedelta(days=days_trial)
        self.moderated_at = timezone.now()
        self.moderated_by = moderator
        self.moderation_note = f'Одобрено. Триал {days_trial} дней.'
        self.save()
    
    def reject(self, moderator, reason=''):
        """Отклонить ресторан"""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.moderated_at = timezone.now()
        self.moderated_by = moderator
        self.moderation_note = reason or 'Заявка отклонена.'
        self.save()


class UserProfile(models.Model):
    """Профиль пользователя — связь с рестораном и роль"""
    
    ROLE_CHOICES = [
        ('super_admin', 'Супер-админ'),
        ('owner', 'Владелец'),
        ('manager', 'Менеджер'),
        ('cashier', 'Кассир'),
    ]
    
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff',
        verbose_name='Ресторан'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='owner',
        verbose_name='Роль'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    
    # Email-верификация
    email_verified = models.BooleanField(default=False, verbose_name='Email подтверждён')
    email_verification_token = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='Токен верификации'
    )
    email_verification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Когда отправлено'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Category(models.Model):
    """Категория блюд (Пицца, Напитки, Десерты)"""
    
    PRINTER_CHOICES = [
        ('kitchen', 'Кухня'),
        ('bar', 'Бар'),
        ('cold', 'Холодный цех'),
    ]
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='Ресторан',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100, verbose_name='Название')
    printer_target = models.CharField(
        max_length=20,
        choices=PRINTER_CHOICES,
        default='kitchen',
        verbose_name='Куда печатать'
    )
    sort_order = models.IntegerField(default=0, verbose_name='Порядок')
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """Блюдо в меню"""
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='Ресторан',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Категория'
    )
    image = models.ImageField(
        upload_to='menu/',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    weight = models.IntegerField(default=0, verbose_name='Вес (г)')
    is_available = models.BooleanField(default=True, verbose_name='Доступно')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Блюда'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} — {self.price}₽"


class Table(models.Model):
    """Столик в ресторане"""
    
    SHAPE_CHOICES = [
        ('square', 'Квадрат'),
        ('circle', 'Круг'),
        ('rect', 'Прямоугольник'),
    ]
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='tables',
        verbose_name='Ресторан',
        null=True,
        blank=True
    )
    number = models.IntegerField(verbose_name='Номер стола')
    qr_token = models.CharField(
        max_length=32,
        unique=True,
        default=generate_qr_token,
        verbose_name='Токен QR'
    )
    zone = models.CharField(max_length=50, blank=True, verbose_name='Зал')
    is_busy = models.BooleanField(default=False, verbose_name='Занят')
    
    # === НОВЫЕ ПОЛЯ ДЛЯ СХЕМЫ ЗАЛА ===
    position_x = models.IntegerField(
        default=50,
        verbose_name='Позиция X',
        help_text='Отступ слева в пикселях'
    )
    position_y = models.IntegerField(
        default=50,
        verbose_name='Позиция Y',
        help_text='Отступ сверху в пикселях'
    )
    width = models.IntegerField(
        default=100,
        verbose_name='Ширина',
        help_text='Ширина стола в пикселях'
    )
    height = models.IntegerField(
        default=100,
        verbose_name='Высота',
        help_text='Высота стола в пикселях'
    )
    shape = models.CharField(
        max_length=20,
        choices=SHAPE_CHOICES,
        default='square',
        verbose_name='Форма'
    )
    # === КОНЕЦ НОВЫХ ПОЛЕЙ ===
    
    class Meta:
        verbose_name = 'Столик'
        verbose_name_plural = 'Столики'
        ordering = ['number']
        unique_together = [['restaurant', 'number']]
    
    def __str__(self):
        return f"Стол №{self.number}"


class Order(models.Model):
    """Заказ"""
    
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('cooking', 'Готовится'),
        ('ready', 'Готов'),
        ('served', 'Подан'),
        ('paid', 'Оплачен'),
        ('cancelled', 'Отменён'),
    ]
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Ресторан',
        null=True,
        blank=True
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        verbose_name='Столик'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name='Статус'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Сумма'
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлён')
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
    
    def __str__(self):
        table_num = self.table.number if self.table else '?'
        return f"Заказ #{self.id} — Стол {table_num}"
    
    def calculate_total(self):
        total = sum(item.price * item.quantity for item in self.items.all())
        self.total_price = total
        self.save()
        return total


class OrderItem(models.Model):
    """Позиция заказа"""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        verbose_name='Блюдо'
    )
    quantity = models.IntegerField(default=1, verbose_name='Количество')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена'
    )
    
    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"


class Printer(models.Model):
    """Сетевой принтер (Xprinter или другой ESC/POS)"""
    
    TARGET_CHOICES = [
        ('kitchen', 'Кухня'),
        ('bar', 'Бар'),
        ('cold', 'Холодный цех'),
        ('cashier', 'Касса'),
    ]
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='printers',
        verbose_name='Ресторан',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100, verbose_name='Название')
    target = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        verbose_name='Цех'
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IP-адрес',
        help_text='Оставьте пустым, заполните после настройки принтера'
    )
    port = models.IntegerField(default=9100, verbose_name='Порт')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_fallback = models.BooleanField(
        default=False,
        verbose_name='Принтер по умолчанию (fallback)',
        help_text='Если для цеха нет принтера — заказ уйдёт сюда'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Принтер'
        verbose_name_plural = 'Принтеры'
        ordering = ['target', 'name']
    
    def __str__(self):
        status = self.ip_address if self.ip_address else 'IP не задан'
        fallback = ' [FALLBACK]' if self.is_fallback else ''
        return f"{self.name} ({self.get_target_display()}){fallback} — {status}"
    
    @property
    def is_configured(self):
        return bool(self.ip_address) and self.is_active
    
    @classmethod
    def get_fallback(cls):
        return cls.objects.filter(is_fallback=True, is_active=True).first()


class FailedPrintJob(models.Model):
    """Заказ, который не удалось напечатать — для кассы"""
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='failed_prints',
        verbose_name='Ресторан',
        null=True,
        blank=True
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='failed_prints',
        verbose_name='Заказ'
    )
    target = models.CharField(max_length=20, verbose_name='Цех')
    reason = models.CharField(max_length=50, verbose_name='Причина')
    is_resolved = models.BooleanField(default=False, verbose_name='Обработано')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Неудачная печать'
        verbose_name_plural = 'Неудачные печати'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заказ #{self.order.id} → {self.target} ({self.reason})"


class Agent(models.Model):
    """Локальный агент (Raspberry Pi)"""
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='agents',
        verbose_name='Ресторан',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100, verbose_name='Название')
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_agent_token,
        verbose_name='Токен'
    )
    restaurant_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ресторан'
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последняя активность'
    )
    is_online = models.BooleanField(default=False, verbose_name='Онлайн')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Агент'
        verbose_name_plural = 'Агенты'
    
    def __str__(self):
        status = '🟢' if self.is_online else '🔴'
        return f"{status} {self.name}"