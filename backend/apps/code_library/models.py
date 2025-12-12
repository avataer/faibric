import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class LibraryCategory(models.Model):
    """
    Category for organizing library items.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Hierarchy
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Display
    icon = models.CharField(max_length=50, blank=True, default='📁')
    color = models.CharField(max_length=20, blank=True, default='#3B82F6')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Library Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class LibraryItem(models.Model):
    """
    A reusable code item in the library.
    Can be a component, service, utility, template, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='library_items',
        null=True,
        blank=True,
        help_text="Null for global/shared items"
    )
    
    # Identification
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    
    TYPE_CHOICES = [
        ('component', 'Component'),
        ('service', 'Service'),
        ('utility', 'Utility'),
        ('template', 'Template'),
        ('hook', 'React Hook'),
        ('api', 'API Endpoint'),
        ('model', 'Data Model'),
        ('style', 'Style/CSS'),
        ('config', 'Configuration'),
        ('snippet', 'Code Snippet'),
    ]
    item_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Category
    category = models.ForeignKey(
        LibraryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )
    
    # Content
    LANGUAGE_CHOICES = [
        ('typescript', 'TypeScript'),
        ('javascript', 'JavaScript'),
        ('python', 'Python'),
        ('html', 'HTML'),
        ('css', 'CSS'),
        ('json', 'JSON'),
        ('yaml', 'YAML'),
        ('markdown', 'Markdown'),
        ('sql', 'SQL'),
        ('shell', 'Shell'),
    ]
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    
    # The actual code
    code = models.TextField()
    
    # Documentation
    description = models.TextField(blank=True)
    usage_example = models.TextField(blank=True)
    documentation = models.TextField(blank=True)
    
    # Search metadata
    keywords = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Embedding for semantic search (stored as JSON array of floats)
    embedding = models.JSONField(null=True, blank=True, help_text="Vector embedding for semantic search")
    embedding_model = models.CharField(max_length=100, blank=True, default='text-embedding-3-small')
    
    # Dependencies
    dependencies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of npm/pip packages required"
    )
    requires = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='required_by',
        help_text="Other library items this depends on"
    )
    
    # Quality metrics
    quality_score = models.FloatField(
        default=0.0,
        help_text="0-100 quality score"
    )
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Source tracking
    SOURCE_CHOICES = [
        ('generated', 'AI Generated'),
        ('imported', 'Imported'),
        ('manual', 'Manually Added'),
        ('curated', 'Curated/Official'),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='generated')
    source_url = models.URLField(blank=True)
    
    # Author info
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_library_items'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False, help_text="Available to all tenants")
    is_deprecated = models.BooleanField(default=False)
    deprecation_note = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-quality_score', '-usage_count', 'name']
        unique_together = [['tenant', 'slug']]
        indexes = [
            models.Index(fields=['tenant', 'item_type']),
            models.Index(fields=['language', 'item_type']),
            models.Index(fields=['is_active', 'is_public']),
            models.Index(fields=['quality_score']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.item_type})"
    
    def increment_usage(self):
        """Record a usage of this item."""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])


class LibraryVersion(models.Model):
    """
    Version history for library items.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        LibraryItem,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    
    # Version info
    version = models.CharField(max_length=20, help_text="Semantic version (e.g., 1.0.0)")
    code = models.TextField()
    
    # Changes
    changelog = models.TextField(blank=True)
    
    # Snapshot of metadata at this version
    dependencies = models.JSONField(default=list, blank=True)
    
    # Author
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['item', 'version']]
    
    def __str__(self):
        return f"{self.item.name} v{self.version}"


class LibraryItemUsage(models.Model):
    """
    Track where library items are used.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        LibraryItem,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    
    # Where it was used
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='library_usages'
    )
    file_path = models.CharField(max_length=500)
    
    # How it was used
    USAGE_TYPE_CHOICES = [
        ('direct', 'Direct Copy'),
        ('modified', 'Modified'),
        ('referenced', 'Referenced'),
    ]
    usage_type = models.CharField(max_length=20, choices=USAGE_TYPE_CHOICES)
    
    # Feedback
    was_helpful = models.BooleanField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.item.name} used in {self.project.name}"


class Constraint(models.Model):
    """
    Constraint definition for code generation.
    Constraints are loaded from MD files and applied during generation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='constraints',
        null=True,
        blank=True,
        help_text="Null for global constraints"
    )
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    
    TYPE_CHOICES = [
        ('security', 'Security'),
        ('styling', 'Styling'),
        ('architecture', 'Architecture'),
        ('api', 'API Usage'),
        ('database', 'Database'),
        ('react', 'React Patterns'),
        ('python', 'Python Patterns'),
        ('custom', 'Custom'),
    ]
    constraint_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Content
    content = models.TextField(help_text="Markdown content of the constraint")
    
    # Parsed rules (extracted from content for quick access)
    rules = models.JSONField(
        default=list,
        blank=True,
        help_text="Parsed list of rules"
    )
    
    # Applicability
    applies_to = models.JSONField(
        default=list,
        blank=True,
        help_text="Languages/item types this applies to"
    )
    
    # Priority (higher = more important)
    priority = models.IntegerField(default=50)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'name']
        unique_together = [['tenant', 'slug']]
    
    def __str__(self):
        return f"{self.name} ({self.constraint_type})"


class ResearchCache(models.Model):
    """
    Cache for research results to avoid repeated lookups.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Query info
    query = models.TextField()
    query_hash = models.CharField(max_length=64, unique=True, db_index=True)
    
    RESEARCH_TYPE_CHOICES = [
        ('web', 'Web Search'),
        ('github', 'GitHub'),
        ('npm', 'NPM'),
        ('pypi', 'PyPI'),
        ('docs', 'Documentation'),
    ]
    research_type = models.CharField(max_length=20, choices=RESEARCH_TYPE_CHOICES)
    
    # Results
    results = models.JSONField(default=list)
    summary = models.TextField(blank=True)
    
    # Metadata
    result_count = models.IntegerField(default=0)
    
    # Expiration
    expires_at = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Research Cache"
    
    def __str__(self):
        return f"{self.research_type}: {self.query[:50]}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at









