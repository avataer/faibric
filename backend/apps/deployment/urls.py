from django.urls import path
from .views import deploy_project, undeploy_project, deployment_status

urlpatterns = [
    path('<int:project_id>/', deploy_project, name='deploy_project'),
    path('<int:project_id>/undeploy/', undeploy_project, name='undeploy_project'),
    path('<int:project_id>/status/', deployment_status, name='deployment_status'),
]

