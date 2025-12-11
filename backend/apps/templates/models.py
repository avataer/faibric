from django.db import models


class Template(models.Model):
    """Pre-built app templates"""
    CATEGORY_CHOICES = [
        ('dashboard', 'Dashboard'),
        ('crud', 'CRUD Application'),
        ('blog', 'Blog/CMS'),
        ('ecommerce', 'E-commerce'),
        ('social', 'Social Network'),
        ('tool', 'Utility Tool'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Template definition
    schema_template = models.JSONField(help_text='Database schema template')
    api_template = models.JSONField(help_text='API endpoints template')
    ui_template = models.JSONField(help_text='UI components template')
    
    # Metadata
    thumbnail = models.ImageField(upload_to='templates/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-usage_count', 'name']
    
    def __str__(self):
        return self.name

