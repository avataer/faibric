from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Project(models.Model):
    """Model for user projects"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('building', 'Building'),      # AI generating code
        ('ready', 'Ready'),            # Code generated, ready to deploy
        ('deploying', 'Deploying'),    # Deployment in progress
        ('deployed', 'Deployed'),      # Live and running
        ('failed', 'Failed'),          # Build or deploy failed
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

    # AI Model preference
    MODEL_CHOICES = [
        ("claude-opus", "Claude Opus 4.5 - Most Powerful"),
        ("claude-sonnet", "Claude Sonnet 4 - Balanced"),
        ("claude-haiku", "Claude Haiku 3.5 - Fast"),
        ("gpt-4o", "GPT-4o - OpenAI Flagship"),
        ("gemini-2-flash", "Gemini 2.0 Flash - Google Fast"),
    ]
    preferred_model = models.CharField(
        max_length=50,
        choices=MODEL_CHOICES,
        default="claude-opus",
        null=True,
        blank=True,
        help_text="AI model to use for code generation"
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

    # GitHub sync
    github_repo = models.CharField(max_length=255, blank=True, default='', help_text="GitHub repo URL")
    last_github_sha = models.CharField(max_length=40, blank=True, default='', help_text="Last synced commit SHA")
    
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

    def get_model_display_name(self) -> str:
        """Return the display name for the preferred AI model."""
        model_dict = dict(self.MODEL_CHOICES)
        return model_dict.get(self.preferred_model, self.preferred_model or "Claude Opus 4.5")


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


class CustomerAPIKey(models.Model):
    """
    Store customer's API keys for data integrations.
    
    Customers can provide their own API keys to unlock real data
    in their generated apps. Keys are encrypted at rest.
    """
    SERVICE_CHOICES = [
        ('openweather', 'OpenWeather'),
        ('alpha_vantage', 'Alpha Vantage (Stocks)'),
        ('finnhub', 'Finnhub (Stocks)'),
        ('newsapi', 'News API'),
        ('stripe', 'Stripe'),
        ('shopify', 'Shopify'),
        ('custom', 'Custom API'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('active', 'Active'),
        ('invalid', 'Invalid'),
        ('expired', 'Expired'),
    ]
    
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='api_keys'
    )
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    service_name = models.CharField(max_length=100, blank=True, help_text='Display name')
    
    # Encrypted API key (should use django-encrypted-model-fields in production)
    api_key = models.CharField(max_length=500)
    
    # For custom APIs
    base_url = models.URLField(blank=True, help_text='For custom APIs')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    last_verified_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Usage tracking
    call_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['project', 'service']]
        verbose_name = 'Customer API Key'
        verbose_name_plural = 'Customer API Keys'
    
    def __str__(self):
        return f"{self.project.name} - {self.service}"
    
    def mask_key(self) -> str:
        """Return masked version of key for display"""
        if len(self.api_key) > 8:
            return f"{self.api_key[:4]}...{self.api_key[-4:]}"
        return "****"

