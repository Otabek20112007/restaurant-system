from django.contrib import admin
from .models import (
    Category, MenuItem, Table, Order, OrderItem,
    Printer, FailedPrintJob, Agent, Restaurant, UserProfile
)


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'slug', 'status', 'owner',
        'trial_ends_at', 'paid_until', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'slug', 'owner__email']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'moderated_at', 'moderated_by']
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'status', 'owner')
        }),
        ('Контакты', {
            'fields': ('address', 'phone')
        }),
        ('Дизайн', {
            'fields': ('logo', 'primary_color', 'secondary_color')
        }),
        ('Настройки', {
            'fields': ('currency', 'language')
        }),
        ('Подписка', {
            'fields': ('trial_ends_at', 'paid_until')
        }),
        ('Модерация', {
            'fields': ('moderation_note', 'moderated_at', 'moderated_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_restaurants', 'reject_restaurants']
    
    @admin.action(description='✅ Одобрить и запустить триал 7 дней')
    def approve_restaurants(self, request, queryset):
        count = 0
        for restaurant in queryset:
            restaurant.approve(request.user, days_trial=7)
            count += 1
        self.message_user(request, f'Одобрено ресторанов: {count}')
    
    @admin.action(description='❌ Отклонить')
    def reject_restaurants(self, request, queryset):
        count = 0
        for restaurant in queryset:
            restaurant.reject(request.user, reason='Отклонено администратором')
            count += 1
        self.message_user(request, f'Отклонено ресторанов: {count}')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'printer_target', 'sort_order', 'restaurant']
    list_filter = ['restaurant', 'printer_target']
    list_editable = ['printer_target', 'sort_order']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available', 'restaurant']
    list_filter = ['restaurant', 'category', 'is_available']
    list_editable = ['price', 'is_available']
    search_fields = ['name']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'zone', 'is_busy', 'restaurant', 'shape', 'qr_token']
    list_filter = ['restaurant', 'is_busy', 'zone', 'shape']
    list_editable = ['is_busy', 'zone']
    readonly_fields = ['qr_token']
    search_fields = ['number', 'zone']
    
    fieldsets = (
        ('Основное', {
            'fields': ('restaurant', 'number', 'zone', 'is_busy', 'qr_token')
        }),
        ('Схема зала', {
            'fields': ('position_x', 'position_y', 'width', 'height', 'shape'),
            'description': 'Координаты и размеры стола на схеме зала'
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'status', 'total_price', 'restaurant', 'created_at']
    list_filter = ['restaurant', 'status', 'created_at']
    list_editable = ['status']
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'target', 'ip_address', 'port',
        'is_active', 'is_fallback', 'restaurant', 'is_configured'
    ]
    list_filter = ['restaurant', 'target', 'is_active', 'is_fallback']
    list_editable = ['ip_address', 'port', 'is_active', 'is_fallback']
    search_fields = ['name', 'ip_address']
    
    fieldsets = (
        ('Основное', {
            'fields': ('restaurant', 'name', 'target', 'is_active')
        }),
        ('Сетевое подключение', {
            'fields': ('ip_address', 'port'),
            'description': 'IP можно оставить пустым — заполните, когда принтер появится.'
        }),
        ('Резервный принтер', {
            'fields': ('is_fallback',),
            'description': 'Если для цеха нет принтера — заказ уйдёт сюда.'
        }),
    )


@admin.register(FailedPrintJob)
class FailedPrintJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'target', 'reason', 'is_resolved', 'restaurant', 'created_at']
    list_filter = ['restaurant', 'target', 'reason', 'is_resolved']
    list_editable = ['is_resolved']
    readonly_fields = ['order', 'target', 'reason', 'created_at']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'is_online', 'last_seen']
    list_filter = ['restaurant', 'is_online']
    readonly_fields = ['token', 'last_seen', 'created_at']

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'Профиль'
    verbose_name_plural = 'Профили'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'is_active', 'get_role', 'get_restaurant'
    ]
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'profile__role']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '—'
    get_role.short_description = 'Роль'
    
    def get_restaurant(self, obj):
        if hasattr(obj, 'profile') and obj.profile.restaurant:
            return obj.profile.restaurant.name
        return '—'
    get_restaurant.short_description = 'Ресторан'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)