from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_stocks, name='get_stocks'),
    path('<str:symbol>/', views.get_stock_detail, name='get_stock_detail'),
]



