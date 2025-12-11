from django.urls import path
from . import views

urlpatterns = [
    # Database Service
    path('db/<int:app_id>/<str:collection_name>/', views.db_collection, name='db_collection'),
    path('db/<int:app_id>/<str:collection_name>/<uuid:doc_id>/', views.db_document, name='db_document'),
    path('db/<int:app_id>/<str:collection_name>/clear/', views.db_collection_delete, name='db_collection_delete'),
    
    # Auth Service
    path('auth/<int:app_id>/signup/', views.auth_signup, name='auth_signup'),
    path('auth/<int:app_id>/login/', views.auth_login, name='auth_login'),
    path('auth/<int:app_id>/users/', views.auth_users, name='auth_users'),
]



