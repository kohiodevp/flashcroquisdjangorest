import uuid
from django.db import models
from django.conf import settings
from PyQt5.QtCore import QDateTime

class ProjectSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    project_title = models.CharField(max_length=255, default="Nouveau Projet")
    project_crs = models.CharField(max_length=50, default="EPSG:4326")
    project_file = models.FileField(upload_to='projects/', null=True, blank=True)
    temporary_files = models.JSONField(default=list)
    
    class Meta:
        db_table = 'project_sessions'
        verbose_name = "Session de projet"
        verbose_name_plural = "Sessions de projet"

    def __str__(self):
        return f"{self.project_title} ({self.session_id})"

    @property
    def created_at_iso(self):
        return self.created_at.toPython().isoformat() if isinstance(self.created_at, QDateTime) else self.created_at.isoformat()

    @property
    def last_accessed_iso(self):
        return self.last_accessed.toPython().isoformat() if isinstance(self.last_accessed, QDateTime) else self.last_accessed.isoformat()

class Layer(models.Model):
    LAYER_TYPES = (
        ('vector', 'Vectoriel'),
        ('raster', 'Raster'),
        ('unknown', 'Inconnu'),
    )
    
    GEOMETRY_TYPES = (
        ('point', 'Point'),
        ('line', 'Ligne'),
        ('polygon', 'Polygone'),
        ('unknown', 'Inconnu'),
    )
    
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='layers')
    layer_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    source = models.TextField(null=True, blank=True)
    crs = models.CharField(max_length=50, null=True, blank=True)
    layer_type = models.CharField(max_length=10, choices=LAYER_TYPES, default='unknown')
    geometry_type = models.CharField(max_length=10, choices=GEOMETRY_TYPES, default='unknown')
    feature_count = models.IntegerField(default=0)
    extent = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'layers'
        unique_together = ('session', 'layer_id')
        verbose_name = "Couche"
        verbose_name_plural = "Couches"

    def __str__(self):
        return f"{self.name} ({self.layer_type})"

class ProcessingJob(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    )
    
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='jobs')
    algorithm = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'processing_jobs'
        verbose_name = "Traitement"
        verbose_name_plural = "Traitements"

    def __str__(self):
        return f"{self.algorithm} - {self.status}"

class GeneratedFile(models.Model):
    FILE_TYPES = (
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('project', 'Projet QGIS'),
        ('other', 'Autre'),
    )
    
    file_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProjectSession, on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file_path = models.FileField(upload_to='generated_files/')
    size = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'generated_files'
        verbose_name = "Fichier généré"
        verbose_name_plural = "Fichiers générés"

    def __str__(self):
        return f"{self.name} ({self.file_type})"