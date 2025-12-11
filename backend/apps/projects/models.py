from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Project(models.Model):
    """Model for user projects"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('deployed', 'Deployed'),
        ('failed', 'Failed'),
    ]
    
    # Tenant isolation - all projects belong to a tenant
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='projects',
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    template = models.ForeignKey(
        'templates.Template', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='projects'
    )
    
    # Generation metadata
    user_prompt = models.TextField(help_text='Original user description')
    ai_analysis = models.JSONField(null=True, blank=True)
    
    # Generated code storage
    database_schema = models.JSONField(null=True, blank=True)
    api_code = models.TextField(blank=True)
    frontend_code = models.TextField(blank=True)
    
    # Deployment info
    subdomain = models.CharField(max_length=100, unique=True, null=True, blank=True)
    deployment_url = models.URLField(blank=True)
    container_id = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deployed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['tenant', 'user', 'name']]
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'user']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"


class GeneratedModel(models.Model):
    """Store individual models generated for a project"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    fields = models.JSONField(help_text='Field definitions')
    relationships = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        unique_together = [['project', 'name']]
    
    def __str__(self):
        return f"{self.name} ({self.project.name})"


class GeneratedAPI(models.Model):
    """Store individual API endpoints generated for a project"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='apis')
    path = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    handler_code = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['path']
        unique_together = [['project', 'path', 'method']]
    
    def __str__(self):
        return f"{self.method} {self.path} ({self.project.name})"


class ProjectVersion(models.Model):
    """Track versions of a project"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=20)
    snapshot = models.JSONField(help_text='Complete snapshot of project state')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['project', 'version']]
    
    def __str__(self):
        return f"{self.project.name} v{self.version}"

