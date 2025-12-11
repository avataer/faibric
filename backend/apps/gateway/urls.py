from django.urls import path
from . import views

urlpatterns = [
    path('', views.gateway, name='gateway'),
    path('services/', views.services_list, name='services_list'),
]



