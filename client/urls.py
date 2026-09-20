from django.urls import path
from . import views

app_name = 'client'

urlpatterns = [
    # Меню для столика (по токену)
    path('r/<slug:restaurant_slug>/t/<str:token>/', 
         views.table_menu, name='table_menu'),
    
    # API: создать заказ
    path('r/<slug:restaurant_slug>/t/<str:token>/order/', 
         views.create_order, name='create_order'),
    
    # Статус заказа
    path('r/<slug:restaurant_slug>/order/<int:order_id>/', 
         views.order_status, name='order_status'),
]