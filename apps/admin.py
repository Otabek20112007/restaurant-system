from django.contrib import admin
from .models import (
    Category, MenuItem, Table, Order, OrderItem,
    Printer, FailedPrintJob, Agent
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'printer_target', 'sort_order']
    list_editable = ['printer_target', 'sort_order']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available']
    list_filter = ['category', 'is_available']
    list_editable = ['price', 'is_available']
    search_fields = ['name']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'zone', 'is_busy', 'qr_token']
    list_editable = ['is_busy', 'zone']
    readonly_fields = ['qr_token']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at']
    list_editable = ['status']
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Printer)
class PrinterAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'target', 'ip_address', 'port',
        'is_active', 'is_fallback', 'is_configured'
    ]
    list_filter = ['target', 'is_active', 'is_fallback']
    list_editable = ['ip_address', 'port', 'is_active', 'is_fallback']
    search_fields = ['name', 'ip_address']
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'target', 'is_active')
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
    list_display = ['id', 'order', 'target', 'reason', 'is_resolved', 'created_at']
    list_filter = ['target', 'reason', 'is_resolved']
    list_editable = ['is_resolved']
    readonly_fields = ['order', 'target', 'reason', 'created_at']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant_name', 'is_online', 'last_seen']
    list_filter = ['is_online']
    readonly_fields = ['token', 'last_seen', 'created_at']