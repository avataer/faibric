from django.urls import path
from .views import generate_app, refine_code, generation_status

urlpatterns = [
    path('generate/', generate_app, name='generate_app'),
    path('refine/<int:project_id>/', refine_code, name='refine_code'),
    path('status/<int:project_id>/', generation_status, name='generation_status'),
]

