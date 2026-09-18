from django.db import models
import secrets


def generate_qr_token():
    """Генерирует случайный токен для QR-кода столика"""
    return secrets.token_urlsafe(16)


def generate_agent_token():
    """Генерирует токен для агента (Raspberry Pi)"""
    return secrets.token_urlsafe(32)


class Category(models.Model):
    """Категория блюд (Пицца, Напитки, Десерты)"""
    
    PRINTER_CHOICES = [
        ('kitchen', 'Кухня'),
        ('bar', 'Бар'),
        ('cold', 'Холодный цех'),
    ]
    
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
    
    number = models.IntegerField(unique=True, verbose_name='Номер стола')
    qr_token = models.CharField(
        max_length=32,
        unique=True,
        default=generate_qr_token,
        verbose_name='Токен QR'
    )
    zone = models.CharField(max_length=50, blank=True, verbose_name='Зал')
    is_busy = models.BooleanField(default=False, verbose_name='Занят')
    
    class Meta:
        verbose_name = 'Столик'
        verbose_name_plural = 'Столики'
        ordering = ['number']
    
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