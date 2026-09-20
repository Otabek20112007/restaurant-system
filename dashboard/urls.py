from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Авторизация
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Обзор
    path('', views.index, name='index'),
    
    # Меню
    path('menu/', views.menu_view, name='menu'),
    path('menu/category/new/', views.category_create, name='category_create'),
    path('menu/category/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('menu/category/<int:category_id>/delete/', views.category_delete, name='category_delete'),
    path('menu/item/new/', views.item_create, name='item_create'),
    path('menu/item/<int:item_id>/edit/', views.item_edit, name='item_edit'),
    path('menu/item/<int:item_id>/delete/', views.item_delete, name='item_delete'),

    # Столики
    path('tables/', views.tables_view, name='tables'),
    path('tables/new/', views.table_create, name='table_create'),
    path('tables/<int:table_id>/edit/', views.table_edit, name='table_edit'),
    path('tables/<int:table_id>/delete/', views.table_delete, name='table_delete'),
    path('tables/<int:table_id>/qr/', views.table_qr, name='table_qr'),
    path('tables/<int:table_id>/qr/image.png', views.table_qr_image, name='table_qr_image'),

    # Заказы
    path('orders/', views.orders_view, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/status/', views.order_change_status, name='order_change_status'),

    # Схема зала
    path('floor-plan/', views.floor_plan_view, name='floor_plan'),
    path('floor-plan/api/save/', views.floor_plan_save, name='floor_plan_save'),
]