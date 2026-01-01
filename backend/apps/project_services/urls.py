"""
Project Services API URLs
"""
from django.urls import path
from . import views

urlpatterns = [
    # Database
    path('database/provision/', views.provision_database, name='provision-database'),
    path('database/<str:project_id>/tables/', views.manage_tables, name='manage-tables'),
    
    # Auth
    path('auth/<str:project_id>/configure/', views.configure_auth, name='configure-auth'),
    path('auth/<str:project_id>/providers/', views.list_auth_providers, name='auth-providers'),
    
    # Domains
    path('domains/<str:project_id>/', views.list_domains, name='list-domains'),
    path('domains/<str:project_id>/add/', views.add_domain, name='add-domain'),
    path('domains/<str:project_id>/<str:domain>/verify/', views.verify_domain, name='verify-domain'),
    path('domains/<str:project_id>/<str:domain>/remove/', views.remove_domain, name='remove-domain'),
    
    # Payments
    path('payments/<str:project_id>/connect/', views.connect_stripe, name='connect-stripe'),
    path('payments/<str:project_id>/products/', views.manage_products, name='manage-products'),
    
    # Analytics
    path('analytics/<str:project_id>/', views.get_analytics, name='get-analytics'),
    path('analytics/<str:project_id>/track/', views.track_event, name='track-event'),
    
    # Versions
    path('versions/<str:project_id>/', views.list_versions, name='list-versions'),
    path('versions/<str:project_id>/diff/', views.get_version_diff, name='version-diff'),
    path('versions/<str:project_id>/rollback/', views.rollback_version, name='rollback-version'),
    
    # Storage
    path('storage/<str:project_id>/buckets/', views.manage_buckets, name='manage-buckets'),
    path('storage/<str:project_id>/upload/', views.upload_file, name='upload-file'),
    
    # Design Editor
    path('design/<str:project_id>/', views.design_editor, name='design-editor'),
    path('design/<str:project_id>/preview/', views.preview_design, name='preview-design'),
    path('design/tokens/', views.design_tokens, name='design-tokens'),
    
    # Self-Improvement System
    path('feedback/<str:project_id>/', views.submit_feedback, name='submit-feedback'),
    path('improvement/status/', views.improvement_status, name='improvement-status'),
    path('improvement/run/', views.trigger_improvement, name='trigger-improvement'),
    path('improvement/tests/', views.test_registry, name='test-registry'),
]

