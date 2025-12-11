"""
Platform Models - Data storage for generated apps
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class AppCollection(models.Model):
    """
    A collection (like a table) for a specific app.
    Each app can have multiple collections.
    """
    app_id = models.IntegerField(db_index=True)  # Links to Project.id
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['app_id', 'name']
        indexes = [
            models.Index(fields=['app_id', 'name']),
        ]
    
    def __str__(self):
        return f"App {self.app_id} - {self.name}"


class AppDocument(models.Model):
    """
    A document (like a row) in a collection.
    Data is stored as JSON for flexibility.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(AppCollection, on_delete=models.CASCADE, related_name='documents')
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['collection', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.collection.name}/{self.id}"


class AppUser(models.Model):
    """
    A user account for a specific app.
    Each app has its own user namespace.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_id = models.IntegerField(db_index=True)
    email = models.EmailField()
    password_hash = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['app_id', 'email']
        indexes = [
            models.Index(fields=['app_id', 'email']),
        ]
    
    def __str__(self):
        return f"App {self.app_id} - {self.email}"


class AppFile(models.Model):
    """
    A file stored for a specific app.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_id = models.IntegerField(db_index=True)
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.IntegerField()
    path = models.CharField(max_length=500)  # Storage path
    uploaded_by = models.UUIDField(null=True, blank=True)  # AppUser.id
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['app_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"App {self.app_id} - {self.filename}"



