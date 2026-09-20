from django.urls import path
from . import views

app_name = 'cashier'

urlpatterns = [
    path('login/', views.cashier_login, name='login'),
    path('logout/', views.cashier_logout, name='logout'),
    path('', views.index, name='index'),
    
    # API для автообновления
    path('api/orders/', views.orders_api, name='orders_api'),
    path('api/order/<int:order_id>/status/', views.order_change_status, name='order_change_status'),
    path('api/tables/', views.tables_api, name='tables_api'),
    path('api/menu/', views.menu_api, name='menu_api'),
    path('api/create-order/', views.create_order_manual, name='create_order_manual'),
    path('api/failed-prints/', views.failed_prints_api, name='failed_prints_api'),
    path('api/failed-prints/<int:job_id>/resolve/', views.resolve_failed_print, name='resolve_failed_print'),
    path('api/tables-with-status/', views.tables_with_status_api, name='tables_with_status_api'),

    # Полноэкранное окно заказа
    path('order/<int:order_id>/', views.order_fullscreen, name='order_fullscreen'),
    path('api/order/<int:order_id>/add-item/', views.order_add_item, name='order_add_item'),
    path('api/order/<int:order_id>/change-qty/', views.order_change_qty, name='order_change_qty'),
    path('table/<int:table_id>/', views.table_fullscreen, name='table_fullscreen'),
]