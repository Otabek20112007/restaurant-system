from django.urls import path
from . import views

app_name = 'kds'

urlpatterns = [
    path('login/', views.kds_login, name='login'),
    path('logout/', views.kds_logout, name='logout'),
    path('', views.index, name='index'),
    path('api/orders/', views.orders_api, name='orders_api'),
    path('api/order/<int:order_id>/status/', views.order_change_status, name='order_change_status'),
]