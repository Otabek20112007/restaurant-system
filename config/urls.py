from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from apps import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Клиентский API
    path('api/menu/', views.menu_view, name='menu'),
    path('api/table/<str:token>/', views.table_by_token, name='table-by-token'),
    path('api/order/<str:token>/', views.create_order, name='create-order'),
    path('api/order/<int:order_id>/status/', views.order_status, name='order-status'),
    
    # API для кассы
    path('api/cashier/login/', views.cashier_login, name='cashier-login'),
    path('api/cashier/logout/', views.cashier_logout, name='cashier-logout'),
    path('api/cashier/me/', views.cashier_me, name='cashier-me'),
    path('api/cashier/orders/', views.cashier_orders, name='cashier-orders'),
    path('api/cashier/orders/create/', views.cashier_create_order, name='cashier-create-order'),
    path('api/cashier/orders/<int:order_id>/status/', views.cashier_update_order_status, name='cashier-update-status'),
    path('api/cashier/tables/', views.cashier_tables, name='cashier-tables'),
    path('api/cashier/printers/', views.cashier_printers, name='cashier-printers'),
    path('api/cashier/failed-prints/', views.failed_prints, name='failed-prints'),
    path('api/cashier/failed-prints/<int:job_id>/resolve/', views.resolve_failed_print, name='resolve-failed'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)