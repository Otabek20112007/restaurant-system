from django.urls import path
from . import views

app_name = 'auth_app'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('verify-email-sent/', views.verify_email_sent, name='verify_email_sent'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
]