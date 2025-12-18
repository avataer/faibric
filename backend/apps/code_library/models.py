"""
Code Library Models - Reusable components and admin rules.
"""
import uuid
from django.db import models

# Use JSONField instead of ArrayField for SQLite compatibility
# ArrayField is PostgreSQL only


class LibraryCategory(models.Model):
    """Categories for organizing library items."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Library Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class LibraryItem(models.Model):
    """
    Reusable code components curated by admin.
    These are the building blocks for customer projects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(help_text="What this component does")
    
    # Categorization
    ITEM_TYPES = [
        ('component', 'React Component'),
        ('section', 'Page Section'),
        ('page', 'Full Page'),
        ('template', 'Complete Template'),
        ('utility', 'Utility/Helper'),
    ]
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='component')
    category = models.ForeignKey(
        LibraryCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    
    # The actual code
    code = models.TextField(help_text="The React component code")
    language = models.CharField(max_length=20, default='tsx')
    
    # Search & matching
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated keywords for matching (salon, hair, pricing, hero...)"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorization (list of strings)"
    )
    
    # For semantic search
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding for semantic search (list of floats)"
    )
    
    # Quality & usage tracking
    quality_score = models.FloatField(
        default=0.5,
        help_text="0-1 score, higher is better. Set by admin."
    )
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Admin curation
    is_active = models.BooleanField(default=True, help_text="Available for use")
    is_approved = models.BooleanField(default=False, help_text="Approved by admin")
    is_public = models.BooleanField(default=True)
    
    # Source tracking
    source_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Project this was first created for"
    )
    created_by = models.CharField(max_length=50, default='ai', help_text="ai or admin")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-quality_score', '-usage_count']
        indexes = [
            models.Index(fields=['item_type', 'is_active']),
            models.Index(fields=['quality_score']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.item_type})"
    
    def increment_usage(self):
        """Called when this component is used in a project."""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])


class LibraryItemUsage(models.Model):
    """Track which projects used which library items."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(LibraryItem, on_delete=models.CASCADE, related_name='usages')
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='library_usages'
    )
    usage_type = models.CharField(
        max_length=20,
        choices=[('full', 'Used as-is'), ('adapted', 'Adapted'), ('inspired', 'Inspired by')],
        default='adapted'
    )
    was_helpful = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class LibraryVersion(models.Model):
    """Version history for library items."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(LibraryItem, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=20, default='1.0.0')
    code = models.TextField()
    changelog = models.TextField(blank=True)
    created_by = models.CharField(max_length=50, default='system')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['item', 'version_number']
    
    def __str__(self):
        return f"{self.item.name} v{self.version_number}"


class Constraint(models.Model):
    """Design constraints and rules that can be applied to generations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    constraint_type = models.CharField(
        max_length=30,
        choices=[
            ('style', 'Styling Rule'),
            ('layout', 'Layout Rule'),
            ('content', 'Content Rule'),
            ('forbidden', 'Forbidden Pattern'),
            ('required', 'Required Pattern'),
        ],
        default='style'
    )
    rule_text = models.TextField(default='', help_text="The actual constraint text to inject into prompts")
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher priority constraints are applied first")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.constraint_type})"


class ResearchCache(models.Model):
    """Cache for research/analysis results."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.TextField(db_index=True)
    query_hash = models.CharField(max_length=64, unique=True)
    result = models.JSONField(default=dict)
    source = models.CharField(max_length=50, default='ai')
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Cache: {self.query[:50]}..."
    
    @classmethod
    def get_cached(cls, query: str):
        """Get cached result for a query."""
        import hashlib
        from django.utils import timezone
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        try:
            cache = cls.objects.get(query_hash=query_hash)
            if cache.expires_at and cache.expires_at < timezone.now():
                cache.delete()
                return None
            return cache.result
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def set_cached(cls, query: str, result: dict, ttl_hours: int = 24):
        """Cache a result for a query."""
        import hashlib
        from django.utils import timezone
        from datetime import timedelta
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        expires = timezone.now() + timedelta(hours=ttl_hours) if ttl_hours else None
        cls.objects.update_or_create(
            query_hash=query_hash,
            defaults={'query': query, 'result': result, 'expires_at': expires}
        )


class AdminDesignRules(models.Model):
    """
    Admin's art direction and design rules.
    These are injected into every AI prompt to ensure consistency.
    Only ONE active ruleset at a time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100, default="Default Rules")
    is_active = models.BooleanField(default=True, help_text="Only one can be active")
    
    # Typography
    font_rules = models.TextField(
        default="""TYPOGRAPHY RULES:
- Primary font: Apple San Francisco (-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif)
- NEVER use any other font unless explicitly requested
- Headings: Bold, proper hierarchy (h1 > h2 > h3)
- Body text: 16-18px, line-height 1.6
- Never use font sizes below 14px"""
    )
    
    # Colors
    color_rules = models.TextField(
        default="""COLOR RULES:
- Use modern, professional color palettes
- Primary colors should have good contrast
- Always ensure text is readable (WCAG AA minimum)
- Dark mode: Use #0a0a0a or #111111 backgrounds, not pure black
- Gradients: Subtle, professional (not rainbow)
- Accent colors: Use sparingly for CTAs and highlights"""
    )
    
    # Layout
    layout_rules = models.TextField(
        default="""LAYOUT RULES:
- Mobile-first responsive design
- Max content width: 1200px centered
- Consistent padding: 20px mobile, 40px tablet, 60px desktop
- Use CSS Grid or Flexbox, never tables for layout
- Proper spacing between sections (60-100px)
- Hero sections: Full viewport height or at least 600px"""
    )
    
    # Components
    component_rules = models.TextField(
        default="""COMPONENT RULES:
- Buttons: Rounded corners (8-12px), clear hover states
- Cards: Subtle shadows, rounded corners
- Forms: Clear labels, visible focus states
- Images: Always have alt text, use object-fit: cover
- Icons: Consistent size and style throughout"""
    )
    
    # Forbidden patterns
    forbidden_patterns = models.TextField(
        default="""NEVER DO THESE:
- No Lorem Ipsum or placeholder text
- No broken image links or placeholder.jpg
- No inline styles mixing with CSS classes
- No !important unless absolutely necessary
- No fixed pixel widths that break mobile
- No auto-playing videos or audio
- No popup modals on page load
- No Comic Sans, Papyrus, or novelty fonts
- No rainbow gradients or neon colors (unless explicitly requested)
- No stock photo watermarks"""
    )
    
    # Quality standards
    quality_standards = models.TextField(
        default="""QUALITY STANDARDS:
- All components must be self-contained
- Code must be clean and readable
- No console.log statements in production code
- Proper error handling for any data operations
- Accessible: proper ARIA labels, keyboard navigation
- Performance: No unnecessary re-renders"""
    )
    
    # Additional custom rules by admin
    custom_rules = models.TextField(
        blank=True,
        help_text="Any additional rules specific to your brand/style"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Admin Design Rules"
        verbose_name_plural = "Admin Design Rules"
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"
    
    def get_full_rules(self):
        """Combine all rules into a single prompt injection."""
        parts = [
            "=== DESIGN SYSTEM (MANDATORY - FROM ART DIRECTOR) ===",
            self.font_rules,
            self.color_rules,
            self.layout_rules,
            self.component_rules,
            self.forbidden_patterns,
            self.quality_standards,
        ]
        if self.custom_rules:
            parts.append(f"\n=== CUSTOM RULES ===\n{self.custom_rules}")
        return "\n\n".join(parts)
    
    def save(self, *args, **kwargs):
        # Ensure only one active ruleset
        if self.is_active:
            AdminDesignRules.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_rules(cls):
        """Get the currently active design rules."""
        return cls.objects.filter(is_active=True).first()


class CustomerMessage(models.Model):
    """
    Mapping of internal operations to customer-friendly messages.
    Admin can customize what customers see.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Internal operation identifier
    operation_key = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Internal key like 'library_search', 'code_generation', etc."
    )
    
    # What customer sees
    customer_message = models.CharField(
        max_length=200,
        help_text="Friendly message shown to customer"
    )
    
    # Optional variants for variety
    message_variants = models.JSONField(
        default=list,
        blank=True,
        help_text="Alternative messages (list of strings, picked randomly)"
    )
    
    # Timing
    min_display_seconds = models.IntegerField(
        default=2,
        help_text="Minimum time to show this message"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['operation_key']
    
    def __str__(self):
        return f"{self.operation_key} → {self.customer_message}"
    
    def get_message(self):
        """Get a message (random variant if available)."""
        import random
        if self.message_variants:
            return random.choice([self.customer_message] + self.message_variants)
        return self.customer_message
    
    @classmethod
    def get(cls, operation_key, default=None):
        """Get customer message for an operation."""
        try:
            msg = cls.objects.get(operation_key=operation_key, is_active=True)
            return msg.get_message()
        except cls.DoesNotExist:
            return default or f"Working on your project..."


class ReuseLog(models.Model):
    """
    Log of reuse decisions for metrics tracking.
    Used to calculate reuse ratio and monitor system health.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    session_token = models.CharField(max_length=100, db_index=True)
    decision = models.CharField(
        max_length=20,
        choices=[
            ('reused', 'Reused from library'),
            ('generated', 'Generated new'),
            ('gray_zone', 'Gray zone - manual review'),
        ],
        db_index=True
    )
    match_score = models.FloatField(default=0)
    library_item_id = models.CharField(max_length=100, blank=True, null=True)
    candidate_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['decision', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.decision} (score={self.match_score:.1f})"
